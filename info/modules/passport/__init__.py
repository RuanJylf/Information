# 登陆注册等逻辑

from flask import Blueprint

passport_blu = Blueprint("passport", __name__, url_prefix="/passport")

from .views import *