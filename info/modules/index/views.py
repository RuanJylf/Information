from flask import render_template, redirect, session, current_app, request, jsonify, g

from info import constants
from info.libs.paginate_utils import PaginateManage
from info.models import User, News, Category
from info.utils.common import user_login
from info.utils.response_code import RET
from . import index_blu


@index_blu.route("/news_list")
def news_list():
    """
    返回首页新闻列表
    0、我们选择用ajax发送请求
    1、因为设计到分页和分类，所以需要接收两个参数（page，cid）
    2、接收参数。
    3、校验参数
    4、根据不同条件查询，为了将用一条查询语句，需要将查询条件封装到一个filters列表中
    5、将查询进行分页
    6、将数据返回
    :return:
    """
    page = request.args.get("page", "1")
    cid = request.args.get("cid", "1")
    data = PaginateManage.index_paginate(page, cid)
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@index_blu.route("/")
@user_login
def index():
    """
    1、首页右上角信息显示
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

    # news_li = [news.to_basic_dict() for news in news_list]

    # 首页分类显示
    categprys = []
    try:
        categprys = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)

    categpry_dict = [categpry.to_dict() for categpry in categprys]


    data = {
        "user": user.to_dict() if user else None,
        "news_li": news_li,
        "categprys": categpry_dict
    }

    return render_template("news/index.html", data=data)


@index_blu.route("/favicon.ico")
def favicon():
    # 我们还可以让app帮助我们找静态文件
    # current_app.send_static_file('news/favicon.ico')
    return redirect("static/news/favicon.ico")