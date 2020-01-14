from flask import render_template, session, current_app, g, abort, jsonify, request

from info import constants, db
from info.models import User, News, Comment, CommentLike
from info.utils.common import user_login
from info.utils.response_code import RET
from . import news_blu


@news_blu.route("/followed_user", methods=["POST"])
@user_login
def followed_user():
    """
    管制和取消关注
    1、接收被关注用户的id和action
    2、校验参数
    3、查询到关注的用户信息
    4、根据不同操作做不同逻辑
    5、如果是关注，需要判断该用户是否已经关注作者，如果没关注可以将用户添加到作者的粉丝中
    6、如果是未关注，如果已经关注了作者，需要在作者的粉丝中删除该用户
    :return:
    """
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户不存在")

    user_id = request.json.get("user_id")
    action = request.json.get("action")

    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ("follow", "unfollow"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        author = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")

    if not author:
        return jsonify(errno=RET.NODATA, errmsg="被关注的人不存在")

    if action == "follow":
        # 如果是关注行为, 需要判断该用户是否已经关注作者，如果没关注可以将用户添加到作者的粉丝中
        if user not in author.followers:
            author.followers.append(user)
        else:
            jsonify(errno=RET.DATAEXIST, errmsg="当前已经关注")
    else:
        if user in author.followers:
            author.followers.remove(user)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据保存错误")

    return jsonify(errno=RET.OK, errmsg="操作成功")


@news_blu.route('/comment_like', methods=["POST"])
@user_login
def set_comment_like():
    """
    评论点赞
    1、获取评论的用户，并判断是否存在
    2、接收参数（被评论的评论id，行为：取消关注还是关注）
    3、校验参数的完整性，判断是否能转化成整数
    4、通过id校验评论是否存在。
    5、如果是添加点赞，需要先判断用户是否对该条新闻已经点赞（查询）
    6、如果没有点赞，就初始化一个模型，将这次点餐存入到数据库中，并设置点赞数+1
    7、如果是删除点赞，那么需要查处该用户是否点过赞，如果点赞过。直接将其delete
    8、最后统一提交到数据库中。
    9、返回响应。
    :return:
    """

    if not g.user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 获取参数
    comment_id = request.json.get("comment_id")
    action = request.json.get("action")

    # 判断参数
    if not all([comment_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        comment_id = int(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="无效的评论id")

    if action not in ["add", "remove"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询评论数据
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not comment:
        return jsonify(errno=RET.NODATA, errmsg="评论数据不存在")

    if action == "add":
        comment_like = CommentLike.query.filter_by(comment_id=comment_id, user_id=g.user.id).first()
        if not comment_like:
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = g.user.id
            db.session.add(comment_like)
            # 增加点赞条数
            comment.like_count += 1
    else:
        # 删除点赞数据
        comment_like = CommentLike.query.filter_by(comment_id=comment_id, user_id=g.user.id).first()
        if comment_like:
            db.session.delete(comment_like)
            # 减小点赞条数
            comment.like_count -= 1

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="操作失败")
    return jsonify(errno=RET.OK, errmsg="操作成功")


@news_blu.route("/news_comment", methods=["POST"])
@user_login
def news_comment():
    """
    提交评论
    1、获取评论的用户，并判断是否存在
    2、接收参数（被评论的新闻id，评论的内容，如果是评论评论，还需要传parent_id）
    3、校验参数的完整性，判断是否能转化成整数
    4、校验新闻id是否有对应的新闻。
    5、有了user_id和news_id和评论内容，我们可以将这些属性添加到Comment表中
    5、然后添加并提交到数据库。
    6、返回响应，（将新闻评论也返回）为了能够在毁掉的时候显示评论内容及评论人的信息
    :return:
    """
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登陆")

    data = request.json
    news_id = data.get("news_id")
    comment_str = data.get("comment")
    parent_id = data.get("parent_id")

    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    try:
        news_id = int(news_id)
        if parent_id:
            parent_id = int(parent_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据错误")

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="新闻不存在")

    # 初始化Comment
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = comment_str
    if parent_id:
        comment.parent_id = parent_id

    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据库保存失败")

    return jsonify(errno=RET.OK, errmsg="评论成功", comment=comment.to_dict())


@news_blu.route("/news_collect", methods=["POST"])
@user_login
def news_collect():
    """
    一个接口实现新闻收藏和取消收藏（因为收藏和取消收藏大体逻辑一样，所以只需要传入参数不同来判断即可）
    0、先判断用户是否登陆，如果没登陆，不能收藏新闻
    1、接收参数
    2、判断参数的完整性，以及参数是否符合接口文档定义的标准
    3、你需要知道收藏哪条新闻
    4、判断收藏的新闻是否存在。
    5、通过user查询出所收藏的新闻。
    6、如果我们是收藏操作，并且这条新闻不再用户收藏的新闻中，我们就往收藏列表中添加这条新闻
    7、如果我们是取消收藏，并且这条新闻在新闻列表中，那么我们就将他从新闻列表中删除。
    8、最后返回数据
    :return:
    """
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登陆")

    data = request.json
    news_id = data.get('news_id')
    action = data.get('action')

    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据类型不正确")

    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ["collect", "cancel_collect"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="参数错误")

    if not news:
        return jsonify(errno=RET.DATAERR, errmsg="新闻不存在")

    if action == "collect":
        # 如果新闻没有被用户收藏，我们才去收藏
        if news not in user.collection_news:
            user.collection_news.append(news)
    else:
        if news in user.collection_news:
            user.collection_news.remove(news)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)

    return jsonify(errno=RET.OK, errmsg="OK")


@news_blu.route("/<news_id>")
@user_login
def detail(news_id):
    """
    详情页面显示
    :param news_id:
    :return:
    """
    user = g.user
    # 首页点击排行新闻列表显示, 查询出来的是装有每一个对象的列表[obj, obj, obj]
    news_list = []
    try:
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)

    # [{}, {}, {}]
    news_li = []
    for news in news_list:
        news_li.append(news.to_basic_dict())

    # 显示详情页信息
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        abort(404)

    news.clicks += 1
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        abort(500)

    # 详情页显示新闻是否收藏
    is_collected = False
    # 如果用户已经登录，需要显示用户是否收藏，没有登陆，统一为false
    # 那么怎么样才能知道用户是否收藏新闻？
    if user and news in user.collection_news:
        is_collected = True

    # 当我们刚点击详情页面的时候，需要加载评论数据。
    # 1、获取该条新闻的所有评论数据，并按照创建时间降序。
    comments = []
    try:
        comments = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)

    comment_like_ids = []
    if g.user:
        try:
            # 需求：查询当前用户在当前新闻里面都点赞了哪些评论
            # 1. 查询出当前新闻的所有评论 ([COMMENT]) 取到所有的评论id  [1, 2, 3, 4, 5]
            comment_ids = [comment.id for comment in comments]
            # 2. 再查询当前评论中哪些评论被当前用户所点赞 （[CommentLike]）查询comment_id 在第1步的评论id列表内的所有数据 & CommentList.user_id = g.user.id
            comment_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),
                                                     CommentLike.user_id == g.user.id).all()
            # 3. 取到所有被点赞的评论id 第2步查询出来是一个 [CommentLike] --> [3, 5]
            comment_like_ids = [comment_like.comment_id for comment_like in comment_likes]  # [3, 5]
        except Exception as e:
            current_app.logger.error(e)

    comment_dict_li = []
    for comment in comments:
        comment_dict = comment.to_dict()
        # 代表没有点赞
        comment_dict["is_like"] = False
        # 判断当前遍历到的评论是否被当前登录用户所点赞
        if comment.id in comment_like_ids:
            comment_dict["is_like"] = True
        comment_dict_li.append(comment_dict)

    is_followed = False
    # 如果这条新闻有作者，并且用户关注了这个新闻的作者
    # 作者为：news.user 当前新闻被哪个用户发布（为作者）
    # 用户关注了哪些人：g.user.followed
    if news.user and user:
        # 如果作者在用户关注的人中
        if news.user in user.followed:
            is_followed = True
        if user in news.user.followers:
            is_followed = True

    data = {
        "user": user.to_dict() if user else None,
        "news_li": news_li,
        "news": news.to_dict(),
        "is_collected": is_collected,
        "is_followed": is_followed,
        "comment_dict_li": comment_dict_li
    }
    return render_template("news/detail.html", data=data)
