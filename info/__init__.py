import logging
from logging.handlers import RotatingFileHandler
import redis
from flask import Flask, session, current_app, g, render_template
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from config import config


# 先初始化一个db对象，然后用db调用init_app()
from info.utils.common import user_login

db = SQLAlchemy()
redis_store = None # type: redis.StrictRedis

def set_log(config_name):
    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_DEVEL)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10, encoding="utf-8")
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


def create_app(config_name):
    set_log(config_name)
    app = Flask(__name__)

    # 一、从对象中加载配置
    app.config.from_object(config[config_name])

    # 二、配置数据库
    # 1、导入SQLAlchemy
    # 2、初始化一个操作数据库的对象db
    # 3、添加数据库的配置项 SQLALCHEMY_DATABASE_URI 和 SQLALCHEMY_TRACK_MODIFICATIONS
    # 4、在mysql中创建数据库
    # 方法一：直接return db
    # db = SQLAlchemy(app)
    # 方法二：在初始化app的时候传入app
    db.init_app(app)
    # 三、配置redis数据库
    # 1、导入redis包，
    # 2、初始化一个redis的储存对象
    # 3、在配置类中配置主机地址和端口参数
    global redis_store
    redis_store = redis.StrictRedis(host=config[config_name].REDIS_HOST, port=config[config_name].REDIS_PORT, decode_responses=True)

    # 四、开启csrf保护, 而这个csrf集成类只帮我们做保护和验证工作。具体返回到表单中和cookie需要我们自己设定。
    # 1. 在返回响应的时候，往cookie中添加一个csrf_token，2. 并且在表单中添加一个隐藏的csrf_token
    # 2、而我们现在登录或者注册不是使用的表单，而是使用 ajax 请求，所以我们需要在 ajax 请求的时候带上 csrf_token 这个随机值就可以了
    CSRFProtect(app)

    # 五、指定session的储存方式
    # 1、导入flask-session扩展
    # 2、将app集成到session中
    # 3、在配置类中指定储存session的数据库已经设定过期时间等
    # 4、因为session涉及到加密，需要配置secret_key
    Session(app)
    # 加载过滤器到模版
    from info.utils.common import do_index_class
    app.add_template_filter(do_index_class, "index_class")

    # @app.before_request
    # def before_request():
    #     user_id = session.get("user_id", None)
    #     # 必须指定，不指定获取不到user
    #     user = None
    #     if user_id:
    #         try:
    #             from info.models import User
    #             user = User.query.get(user_id)
    #         except Exception as e:
    #             current_app.logger.error(e)
    #     g.user = user
    @app.errorhandler(404)
    @user_login
    def error_handler(_):
        data = {
            "user": g.user.to_dict() if g.user else None
        }
        return render_template("news/404.html", data=data)

    @app.after_request
    def after_request(response):
        """在响应最后设置csrf_token到cookie中"""
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    # 注册蓝图  如何解决循环导入问题？
    from info.modules.index import index_blu
    app.register_blueprint(index_blu)

    from info.modules.passport import passport_blu
    app.register_blueprint(passport_blu)

    from info.modules.news import news_blu
    app.register_blueprint(news_blu)

    from info.modules.profile import profile_blu
    app.register_blueprint(profile_blu)

    from info.modules.admin import admin_blu
    app.register_blueprint(admin_blu)

    return app