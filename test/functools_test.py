import functools


def woshishui(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        print("你不知道我是谁了吧")
        return f(*args, **kwargs)
    return wrapper


@woshishui
def zhangwei():
    print("我是张伟")

@woshishui
def wuxiao():
    print("我是吴潇")


if __name__ == '__main__':
    print(zhangwei.__name__)
    print(wuxiao.__name__)

