from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from info import create_app, db, models
from info.models import User

app = create_app("development")
# 六、数据库的迁移及script的集成
# 1、导入flask-script 和 flask-migrate
# 2、将app与flask-script关联
# 3、将app，db与Migrate关联
# 4、将迁移命令添加到命令中
# 5、通过manager启动项目
manager = Manager(app)
Migrate(app, db)
manager.add_command("db", MigrateCommand)


@manager.option("-p", "--password", dest='password')
@manager.option("-u", "--username", dest='username')
def createsuperuser(username , password):

    if not all([username, password]):
        print("参数不足")

    user = User()
    user.nick_name = username
    user.mobile = username
    user.password = password
    user.is_admin = True

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(e)

    print("创建成功")


if __name__ == "__main__":
    manager.run()