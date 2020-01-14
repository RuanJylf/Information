import random
import re
from datetime import datetime
from flask import request, abort, current_app, make_response, jsonify, session
from info import redis_store, constants, db
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from . import passport_blu


@passport_blu.route('/logout')
def logout():
    """
    只需要把session中的信息删除就可以了
    :return:
    """
    session.pop("user_id", None)
    session.pop("nick_name", None)
    session.pop("mobile", None)
    session.pop("is_admin", None)

    return jsonify(errno=RET.OK, errmsg="退出成功")


@passport_blu.route('/login', methods=["POST"])
def login():
    """
    登录
    1. 获取参数
    2. 校验参数
    3. 校验密码是否正确
        先查询出用户的手机号是否存在。如果存在查出密码
    4. 保存用户的登录状态
    5、更新用户最后一次的登陆时间
    6. 响应
    :return:
    """

    # 1. 获取参数
    params_dict = request.json
    mobile = params_dict.get("mobile")
    password = params_dict.get("password")

    # 2. 校验参数
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 校验手机号是否正确
    if not re.match('1[35678]\\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号格式不正确")

    # 3. 校验密码是否正确
    # 先查询出当前是否有指定手机号的用户
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")
    # 判断用户是否存在
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")

    # 校验登录的密码和当前用户的密码是否一致
    if not user.check_passowrd(password):
        return jsonify(errno=RET.PWDERR, errmsg="用户名或者密码错误")

    # 4. 保存用户的登录状态
    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name

    # 设置当前用户最后一次登录的时间
    user.last_login = datetime.now()

    # 如果在视图函数中，对模型身上的属性有修改，那么需要commit到数据库保存
    # 但是其实可以不用自己去写 db.session.commit(),前提是对SQLAlchemy有过相关配置

    # try:
    #     db.session.commit()
    # except Exception as e:
    #     db.session.rollback()
    #     current_app.logger.error(e)

    # 5. 响应
    return jsonify(errno=RET.OK, errmsg="登录成功")


@passport_blu.route("/register", methods=["POST"])
def register():
    """
    注册的逻辑
    1. 获取参数
    2. 校验参数
    3. 取到服务器保存的真实的短信验证码内容
    4. 校验用户输入的短信验证码内容和真实验证码内容是否一致
    5. 如果一致，初始化 User 模型，并且赋值属性
    6、更新用户的最后一次登陆时间
    7. 将 user 模型添加数据库
    8、保存当天用户登陆状态
    9. 返回响应
    :return: 提示（当操作数据库表的时候，养成打开模型类的习惯）
    """
    # 1. 获取参数
    data = request.json
    mobile = data.get("mobile")
    smscode = data.get("smscode")
    password = data.get("password")

    # 2. 校验参数
    if not all([mobile, smscode, password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数")

    # 校验手机号是否正确
    if not re.match('1[35678]\\d{9}', mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号格式不正确")

    # 3. 取到服务器保存的真实的短信验证码内容
    try:
        real_sms_code = redis_store.get("SMS_" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg="验证码已过期")

    # 4. 校验用户输入的短信验证码内容和真实验证码内容是否一致
    if real_sms_code != smscode:
        return jsonify(errno=RET.DATAERR, errmsg="验证码输入错误")

    # 5. 如果一致，初始化 User 模型，并且赋值属性
    user = User()
    user.mobile = mobile
    # 暂时没有昵称 ，使用手机号代替
    user.nick_name = mobile
    # 记录用户最后一次登录时间
    user.last_login = datetime.now()
    # 对密码做处理
    # 需求：在设置 password 的时候，去对 password 进行加密，并且将加密结果给 user.password_hash 赋值
    user.password = password

    # 6. 添加到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")

    # 往 session 中保存数据表示当前已经登录
    session["user_id"] = user.id
    session["mobile"] = user.mobile
    session["nick_name"] = user.nick_name

    # 7. 返回响应
    return jsonify(errno=RET.OK, errmsg="注册成功")


@passport_blu.route("/sms_code", methods=["POST"])
def send_sms_code():
    """
       发送短信的逻辑
       1. 获取参数：手机号，图片验证码内容，图片验证码的编号 (随机值)
       2. 校验参数(参数是否符合规则，判断是否有值)
       3. 先从redis中取出真实的验证码内容
       4. 与用户的验证码内容进行对比，如果对比不一致，那么返回验证码输入错误
       5. 如果一致，生成验证码的内容(随机数据)
       6. 发送短信验证码
       7、redis中保存短信验证码内容
       8. 告知发送结果
       :return:
    """
    data = request.json
    # 1. 获取参数：手机号，图片验证码内容，图片验证码的编号 (随机值)
    mobile = data.get("mobile")
    image_code = data.get("image_code")
    image_code_id = data.get("image_code_id")

    # 2、校验参数(参数是否符合规则，判断是否有值)
    if not all([mobile, image_code, image_code_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不全")

    if not re.match("^1[3578][0-9]{9}$", mobile):
        return jsonify(errno=RET.DATAERR, errmsg="手机号不正确")

    # 3、先从redis中取出真实的验证码内容
    real_image_code = None
    try:
        real_image_code = redis_store.get("ImageCodeId_"+ image_code_id)
    except Exception as e:
        current_app.logger.error(e)

    if not real_image_code:
        jsonify(errno=RET.NODATA, errmsg="验证码已过期")

    # 4、与用户的验证码内容进行对比，如果对比不一致，那么返回验证码输入错误
    if real_image_code.lower() != image_code.lower():
        return jsonify(errno=RET.DATAERR, errmsg="验证码输入错误")

    # 5. 如果一致，生成验证码的内容(随机数据)
    sms_code_str = "%06d" % random.randint(0, 999999)
    current_app.logger.debug("短信验证码内容是：%s" % sms_code_str)
    # # 6. 发送短信验证码
    # try:
    #     result = CCP().send_template_sms(mobile, [sms_code_str, constants.SMS_CODE_REDIS_EXPIRES/60], 1)
    #     if result != 0:
    #         return jsonify(errno=RET.THIRDERR, errmsg="发送短信失败")
    # except Exception as e:
    #     return jsonify(errno=RET.THIRDERR, errmsg="第三方验证失败")

    # 7、redis中保存短信验证码内容
    try:
        redis_store.set("SMS_" + mobile, sms_code_str, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        # 保存短信验证码失败
        return jsonify(errno=RET.DBERR, errmsg="保存短信验证码失败")

    return jsonify(errno=RET.OK, errmsg="发送成功")


@passport_blu.route("/imageCode")
def get_image_code():
    """
    # 获取图片验证码
    1、接收uuid参数
    2、校验参数是否存在
    3、调用生成验证码的函数生成验证码
    4、将验证码的信息存入redis数据库
    5、返回验证码的二进制数据,默认返回的是text
    6、设置响应头的content-type为image/jpg
    :return:
    """
    imageCodeId = request.args.get("imageCodeId")

    if not imageCodeId:
        abort(403)

    name, text, image = captcha.generate_captcha()
    print(text)
    try:
        redis_store.setex("ImageCodeId_"+ imageCodeId, constants.IMAGE_CODE_REDIS_EXPIRES, text)
    except Exception as e:
        current_app.logger.error(e)
        abort(500)

    response = make_response(image)
    response.headers["Content-Type"] = "image/jpg"

    return response

