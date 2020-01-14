import time

from fabric import env, run
import os

env.user = 'root'
env.hosts = "106.14.134.49"
env.password = "R950413Jylf"
local_project_dir = os.getcwd()

with open("requirements.txt", "r") as f:
    req_list = f.readlines()

requirements = [req.strip() for req in req_list]

virtualenv_dir = "/root/.virtualenvs/flask_py3/bin/"

explain = 'first'


# 创建虚拟环境
def make_virtualenv():
    run("mkvirtualenv -p python3 flask_py3")


# 上传项目文件
def put_dir():
    # 确保有git命令
    run("rm -rf /root/information")
    run("git clone https://github.com/RuanJylf/Information.git")


# 安装第三方包
def install_package():
    for i in requirements:
        run(virtualenv_dir +"pip install {}".format(i))


# 如果已经有表不需要执行
def database_migrate():
    # 确保有数据库
    run("cd /root/information && " + virtualenv_dir + "python manage.py db init", pty=False)
    run("cd /root/information && " + virtualenv_dir + "python manage.py db migrate -m'%s'" % (explain), pty=False)
    run("cd /root/information && " + virtualenv_dir + "python manage.py db upgrade", pty=False)


# 如果已经有数据不需要执行
def import_sql():
    # 确保测试数据在当前项目里面
    run("cd /root/information/ && mysql -u root -pmysql information < information_info_category.sql", pty=False)
    time.sleep(5)
    run("cd /root/information/ && mysql -u root -pmysql information < information_info_news.sql", pty=False)


# 启动项目
def run_project():
    run("cd /root/information/ && " + virtualenv_dir + "gunicorn -w 2 -b 127.0.0.1:5000 manage:app -D --log-level debug --log-file /root/information/logs/log --reload", pty=False)



