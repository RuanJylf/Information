from datetime import datetime, timedelta

from flask import render_template, g, request, current_app, session, redirect, url_for, jsonify

from info import user_login, constants, db
from info.models import User, News, Category
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import admin_blu


@admin_blu.before_request
def before_request():
    """
    1、去判断用户是否为管理员，如果为管理员才能够访问管理员页面，如果不是管理员，重定向到首页
    2、因为设置了请求勾子，所以在我们进入后台登陆页面的时候也需要验证，为了避免，需要处理
    :return:
    """
    is_admin = session.get("is_admin")
    is_url = request.url.endswith(url_for("admin.login"))
    if not is_admin and not is_url:
        return redirect(url_for("index.index"))


@admin_blu.route('/news_type', methods=["GET", "POST"])
def news_type():
    """
    1、新闻分类的显示
    2、新闻分类增加和编辑，使用一个接口
    3、因为增加只需要传分类名字，而编辑需要传id和分类名
    4、所以可以根据是否有分类id来判断行为
    :return:
    """
    if request.method == "GET":
        categories = Category.query.all()
        categories_li = []
        for category in categories:
            c_dict = category.to_dict()
            categories_li.append(c_dict)
        # 移除`最新`分类
        categories_li.pop(0)

        data = {"categories": categories_li}

        return render_template("admin/news_type.html", data=data)

    category_id = request.json.get("id")
    category_name = request.json.get("name")

    if not category_name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if not category_id:
        # 如果没有分类id，说明我们的行为是新增
        category = Category()
        category.name = category_name
        db.session.add(category)
    else:
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")

        if not category:
            return jsonify(errno=RET.NODATA, errmsg="新闻分类不存爱")

        category.name = category_name

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    return jsonify(errno=RET.OK, errmsg="保存数据成功")


@admin_blu.route('/news_edit_detail', methods=["GET", "POST"])
def news_edit_detail():
    """
    新闻编辑
    :param :
    :return:
    """

    if request.method == "GET":
        news_id = request.args.get("news_id")
        if not news_id:
            return render_template('admin/news_edit_detail.html', data={"errmsg": "未查询到此新闻"})
        # 通过id查询新闻
        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template('admin/news_edit_detail.html', data={"errmsg": "未查询到此新闻"})

        # 查询分类的数据
        categories = Category.query.all()
        categories_li = []
        for category in categories:
            c_dict = category.to_dict()
            c_dict["is_selected"] = False
            if category.id == news.category_id:
                c_dict["is_selected"] = True
            categories_li.append(c_dict)
        # 移除`最新`分类
        categories_li.pop(0)

        data = {"news": news.to_dict(), "categories": categories_li}
        return render_template('admin/news_edit_detail.html', data=data)

    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    # 1.1 判断数据是否有值
    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    # 1.2 尝试读取图片
    if index_image:
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
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    # 3. 设置相关数据
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    # 4. 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    # 5. 返回结果
    return jsonify(errno=RET.OK, errmsg="编辑成功")


@admin_blu.route("/news_edit")
def news_edit():
    """
    新闻版式页面数据显示
    :return:
    """
    page = request.args.get("page", 1)
    keywords = request.args.get("keywords", "")

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    filters = [News.status == 0]
    if keywords:
        filters.append(News.title.contains(keywords))

    try:
        paginate = News.query.filter(*filters) \
            .order_by(News.create_time.desc()) \
            .paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_basic_dict())

    context = {"total_page": total_page,
               "current_page": current_page,
               "news_list": news_dict_list
               }
    return render_template('admin/news_edit.html', data=context)


@admin_blu.route('/news_review_detail', methods=["GET", "POST"])
def news_review_detail():
    """
    新闻详情审核
    :param :
    :return:
    """

    if request.method == "GET":

        news_id = request.args.get("news_id")
        if not news_id:
            return render_template('admin/news_review_detail.html', data={"errmsg": "未查询到此新闻"})
        # 通过id查询新闻
        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template('admin/news_review_detail.html', data={"errmsg": "未查询到此新闻"})

        # 返回数据
        data = {"news": news.to_dict()}
        return render_template('admin/news_review_detail.html', data=data)

    # 1.获取参数
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    # 2.判断参数
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ("accept", "reject"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    news = None
    try:
        # 3.查询新闻
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到数据")

    # 4.根据不同的状态设置不同的值
    if action == "accept":
        news.status = 0
    else:
        # 拒绝通过，需要获取原因
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
        news.reason = reason
        news.status = -1

    # 保存数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")
    return jsonify(errno=RET.OK, errmsg="操作成功")


@admin_blu.route("/news_review")
def news_review():
    """
    需审核新闻页面显示
    :return:
    """
    page = request.args.get("page", 1)
    keywords = request.args.get("keywords", "")

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    filters = [News.status != 0]
    if keywords:
        filters.append(News.title.contains(keywords))

    try:
        paginate = News.query.filter(*filters) \
            .order_by(News.create_time.desc()) \
            .paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_review_dict())

    context = {"total_page": total_page,
               "current_page": current_page,
               "news_list": news_dict_list
               }
    return render_template('admin/news_review.html', data=context)


@admin_blu.route("/user_list")
def user_list():
    """
    个人信息列表展示
    查询分页
    :return:
    """
    page = request.args.get("page", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 设置变量默认值
    users = []
    current_page = 1
    total_page = 1

    # 查询数据
    try:
        paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()).paginate(page, constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        users = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    # 将模型列表转成字典列表
    users_list = []
    for user in users:
        users_list.append(user.to_admin_dict())

    data = {"total_page": total_page,
            "current_page": current_page,
            "users": users_list
            }
    return render_template('admin/user_list.html', data=data)


@admin_blu.route("/user_count")
def user_count():
    """
    用户统计
    1、需要显示用户总数
    2、用户月新增人数  （创建时间大于月初）
    3、日新增人数  （创建时间大于当天开始）
    4、用户登陆活跃数。
    :return:
    """
    total_count = 0
    try:
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)

    month_count = 0
    # create_time 是datetime.datetime(2018, 7, 24, 20, 54, 41, 668462) 可以进行比较
    # 1、先找出当月的第一天"2018-07-01"
    # 2、获取当前年份和月份
    now = datetime.now()
    month_begin_date_str = "%d-%02d-01" % (now.year, now.month)
    # 3、然后转化为datetime.datetime类型
    month_begin_date = datetime.strptime(month_begin_date_str, "%Y-%m-%d")
    try:
        month_count = User.query.filter(User.is_admin == False, User.create_time > month_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    day_count = 0
    day_begin_date_str = "%d-%02d-%02d" % (now.year, now.month, now.day)
    # 3、然后转化为datetime.datetime类型
    day_begin_date = datetime.strptime(day_begin_date_str, "%Y-%m-%d")
    try:
        day_count = User.query.filter(User.is_admin == False, User.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    # 拆线图数据

    active_time = []
    active_count = []

    # # 取到今天的时间字符串
    # today_date_str = ('%d-%02d-%02d' % (now.year, now.month, now.day))
    # # 转成时间对象
    # today_date = datetime.strptime(today_date_str, "%Y-%m-%d")

    for i in range(0, 31):
        # 取到某一天的0点0分
        begin_date = day_begin_date - timedelta(days=i)
        # 取到下一天的0点0分
        end_date = day_begin_date - timedelta(days=(i - 1))
        count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                  User.last_login < end_date).count()
        active_count.append(count)
        active_time.append(begin_date.strftime('%Y-%m-%d'))

    # User.query.filter(User.is_admin == False, User.last_login >= 今天0点0分, User.last_login < 今天24点).count()

    # 反转，让最近的一天显示在最后
    active_time.reverse()
    active_count.reverse()

    data = {
        "total_count": total_count,
        "day_count": day_count,
        "month_count": month_count,
        "active_time": active_time,
        "active_count": active_count
    }

    return render_template("admin/user_count.html", data=data)


@admin_blu.route("/index", methods=["GET", "POST"])
@user_login
def index():
    """
    后台首页显示
    :return:
    """
    user = g.user
    return render_template("admin/index.html", user=user.to_admin_dict())


@admin_blu.route("/logout", methods=["GET", "POST"])
def logout():
    """
    退出登陆
    :return:
    """
    session.pop("user_id", None)
    session.pop("nick_name", None)
    session.pop("mobile", None)
    session.pop("is_admin", None)

    return redirect(url_for("index.index"))


@admin_blu.route("/login", methods=["GET", "POST"])
def login():
    """
    管理员登陆页面显示以及登陆
    get:
    1、如果用户已经登陆，并且为admin用户的话，我们就让他直接跳转到后台首页
    post:
    1、接收参数用户名和密码   （因为需要跳转页面，所以接收参数需要用表单的形式）
    2、通过用户名找到密码，校验密码是否正确，以及参数的完整性
    3、校验通过后需要保存用户登陆状态
    4、并且跳转到后台首页
    :return:
    """
    if request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")

        if not all([password, username]):
            return render_template("admin/login.html", errmsg="请输入完整的信息")

        try:
            user = User.query.filter(User.mobile == username).first()
        except Exception as e:
            current_app.logger.error(e)
            return render_template("admin/login.html", errmsg="查询错误")

        if not user:
            return render_template("admin/login.html", errmsg="用户名不存在")

        if not user.check_passowrd(password):
            return render_template("admin/login.html", errmsg="用户名或者密码错误")

        if not user.is_admin:
            return render_template("admin/login.html", errmsg="权限不够")

        session["user_id"] = user.id
        session["mobile"] = user.mobile
        session["nick_name"] = user.nick_name
        session["is_admin"] = True

        return redirect(url_for("admin.index"))

    user_id = session.get("user_id", None)
    is_admin = session.get("is_admin", False)
    if user_id and is_admin:
        return redirect(url_for("admin.index"))

    return render_template("admin/login.html")