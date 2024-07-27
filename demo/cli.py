import logging
import time
import kirei as kr
from kirei import types as krtp

app = kr.CliApplication()
web_app = kr.WebApplication()

logging.basicConfig(level=logging.DEBUG)


@web_app.register()
@app.register()
def echo(msg):
    return msg


@web_app.register()
@app.register()
def add(a: int, b: int):
    return a + b


@app.register()
def long_time_operation():
    time.sleep(5)


@app.register()
def div(a: int, b: int):
    return a / b


@web_app.register()
@app.register()
def file_test(f: kr.UserInputFilePath):
    print(f)


@web_app.register()
@app.register()
def csv_to_xlsx(f: kr.UserInputFilePath) -> kr.OutputFilePath:
    return f


if __name__ == "__main__":
    web_app()
