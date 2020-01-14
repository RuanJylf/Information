# 放一些常用的工具类
import functools

from flask import session, current_app, g


def do_index_class(index):
    """
    自定义过滤器
    :param index:通过传入的下标决定class里面的值
    :return:
    """
    if index == 1:
        return "first"
    elif index == 2:
        return "second"
    elif index == 3:
        return "third"
    return


# 定义用户是否登陆装饰漆
def user_login(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id", None)
        # 必须指定，不指定获取不到user
        user = None
        if user_id:
            try:
                from info.models import User
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
        g.user = user
        return f(*args, **kwargs)
    return wrapper