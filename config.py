import logging

import redis


class Config(object):
    """公有的配置"""
    # 设置secret_key
    SECRET_KEY = "CR7AxRiyzOi21zMvaH312+I0Iy6o95vMgDmYglMihpsHY3yEOrD19QE0MWG0cSkE9vBFxi/3oSYLvfJm2JPzkA=="
    # 配置数据库
    SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://root:mysql@127.0.0.1:3306/information"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 在请求结束时候，如果指定此配置为 True ，那么 SQLAlchemy 会自动执行一次 db.session.commit()操作
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    # 配置redis的ip和port
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379
    # 指定session的储存位置
    SESSION_TYPE = "redis"
    # 设置session签名，也就是所谓的加密
    SESSION_USE_SIGNER = True
    # 设置session不为永久储存
    SESSION_PERMANENT = False
    # 设置session的过期时间
    PERMANENT_SESSION_LIFETIME = 86400 * 2
    # 使用redis
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)


class DevelopmentConfig(Config):
    """开发环境下的配置"""
    # 开启调试模式
    DEBUG = True
    LOG_DEVEL = logging.DEBUG


class ProductionConfig(Config):
    """生产环境下的配置"""
    LOG_DEVEL = logging.ERROR


class TestingConfig(Config):
    """测试环境下的配置"""
    TESTING = True
    LOG_DEVEL = logging.DEBUG


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}