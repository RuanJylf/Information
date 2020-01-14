from flask import render_template, g, redirect, request, jsonify, current_app, session, abort

from info import db, constants
from info.libs.paginate_utils import PaginateManage
from info.models import Category, News, User
from info.utils.common import user_login
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import profile_blu


@profile_blu.route("/other_news_list")
def other_news_list():
    """
    1、其他用户列表新闻展示（因为是整体，当点击第一页和第二页的时候，需要局部刷新，所以用ajax请求发送）
    2、因为只查询该用户的新闻，所以需要传该用户的id和page
    :return:
    """
    other_id = request.args.get("user_id")
    page = request.args.get("page", 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if not all([page, other_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        other = User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not other:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")

    try:
        paginate = other.news_list.paginate(page, constants.OTHER_NEWS_PAGE_MAX_COUNT, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    news_dict_li = [news.to_review_dict() for news in news_li]

    data = {
        "news_list": news_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@profile_blu.route('/other_info')
@user_login
def other_info():
    """
    其他用户信息展示
    :return:
    """
    user = g.user
    other_id = request.args.get("user_id")

    if not other_id:
        abort(404)

    other = None
    try:
        other = User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)

    if not other:
        abort(404)

    is_followed = False
    if user in other.followers:
        is_followed = True

    data = {
        "user": user.to_dict(),
        "other_info": other.to_dict(),
        "is_followed": is_followed
    }
    return render_template("news/other.html", data=data)


@profile_blu.route("/user_follow")
@user_login
def user_follow():
    """
    个人中心显示用户关注
    :return:
    """
    page = request.args.get("page", 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        # 如果出现异常
        page = 1

    user = g.user

    items = []
    current_page = 1
    total_page = 1
    try:
        paginate = user.followed.paginate(page, constants.HOME_PAGE_MAX_NEWS, False)
        items = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    data = {
        "users": [item.to_dict() for item in items],
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("news/user_follow.html", data=data)


@profile_blu.route("/user_news_list")
@user_login
def user_news_list():
    """
    显示出用户发布的新闻列表
    1、接收参数，因为涉及到分页，所以需要 page
    2、校验参数
    3、查询出该用户的发布过的新闻
    4、返回数据
    :return:
    """
    page = request.args.get("page", 1)
    data = PaginateManage.news_list_paginate(page)
    return render_template("news/user_news_list.html", data=data)


@profile_blu.route("/user_news_release", methods=["GET", "POST"])
@user_login
def user_news_release():
    """
    新闻发布（显示）
    1、查询出所有的分类
    2、取出所有的分类字典
    3、删除最新的分类
    新闻发布（提交）
    1、由于是用ajax表单提交
    2、所以在接收参数的时候需要用form
    3、校验参数
    4、将参数存储到新闻中，注意打开新闻的模型类
    5、保存到数据库中
    6、返回数据
    :return:
    """
    if request.method == "GET":
        categorys = []
        try:
            categorys = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
        categorys_dict_li = [category.to_dict() for category in categorys]
        categorys_dict_li.pop(0)
        return render_template("news/user_news_release.html", categorys_dict_li=categorys_dict_li)

    data = request.form
    title = data.get("title")
    digest = data.get("digest")
    content = data.get("content")
    category_id = data.get("category_id")
    index_image = request.files.get("index_image")

    if not all([title, digest, content, index_image, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    try:
        category_id = int(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    # 1.2 尝试读取图片
    try:
        index_image = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    # 2. 将标题图片上传到七牛
    try:
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")

        # 3. 初始化新闻模型，并设置相关数据
    news = News()
    news.title = title
    news.digest = digest
    news.source = "个人发布"
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    news.user_id = g.user.id
    # 1代表待审核状态
    news.status = 1
    # 4. 保存到数据库
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    # 5. 返回结果
    return jsonify(errno=RET.OK, errmsg="发布成功，等待审核")


@profile_blu.route("/user_collection")
@user_login
def user_collection():
    """
    用户收藏显示
    1、接收参数 因为涉及到分页，需要知道 第几页 page
    2、校验参数
    3、从user中取出用户收藏的新闻进行分页
    4、返回数据
    :return:
    """
    page = request.args.get("page", 1)
    data = PaginateManage.news_collection_paginate(page)
    return render_template("news/user_collection.html", data=data)


@profile_blu.route("/user_pass_info", methods=["GET", "POST"])
@user_login
def user_pass_info():
    """
    修改密码
    1、接收请求参数
    2、校验参数
    3、取出该用户的源密码和输入的原密码进行比较
    4、将新密码保存到数据库中
    5、返回响应
    :return:
    """
    if request.method == "GET":
        return render_template("news/user_pass_info.html")

    data = request.json
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    user = g.user
    if not user.check_passowrd(old_password):
        return jsonify(errno=RET.PWDERR, errmsg="密码输入错误")

    user.password = new_password

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")

    return jsonify(errno=RET.OK, errmsg="保存成功")


@profile_blu.route("/user_pic_info", methods=["GET", "POST"])
@user_login
def user_pic_info():
    """
    用户头像显示和上传
    1、接收请求参数
    2、上传头像
    3、储存用户头像为url+七牛云回调值
    4、返回响应
    :return:
    """
    user = g.user
    if request.method == "GET":
        return render_template("news/user_pic_info.html", data=user.to_dict())

    try:
        avatar = request.files.get("avatar").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        key = storage(avatar)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="第三方错误")

    user.avatar_url = key
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据库保存错误")

    return jsonify(errno=RET.OK, errmsg="上传成功", avatar_url=constants.QINIU_DOMIN_PREFIX + key)


@profile_blu.route("/user_base_info", methods=["GET", "POST"])
@user_login
def user_base_info():
    """
    用户基本信息显示和修改 (所以需要两种请求 GET and  POST), ajax
    1、接收请求参数 （nick_name， signature， gender）
    2、校验参数
    3、业务逻辑（将参数保存到user中）
    4、返回响应
    :return:
    """
    user = g.user
    # 因为我们在info试图函数中已经判断过user不存在的情况了，所以不需要再去判断
    if request.method == "GET":
        return render_template("news/user_base_info.html", data=user.to_dict())

    data = request.json
    nick_name = data.get("nick_name")
    signature = data.get("signature")
    gender = data.get("gender")

    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    if gender not in ["MAN", "WOMAN"]:
        return jsonify(errno=RET.DATAERR, errmsg="参数错误")

    user.nick_name = nick_name
    user.signature = signature
    user.gender = gender

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    # 由于我们原来的nick_name为mobile，所以需要重新设定一下
    session["nick_name"] = nick_name

    return jsonify(errno=RET.OK, errmsg="修改成功")


@profile_blu.route("/info")
@user_login
def user_info():
    """
    用户个人中心页面显示
    :return:
    """
    user = g.user
    if not user:
        return redirect("/")
    data = {
        "user": user.to_dict()
    }
    return render_template("news/user.html", data=data)