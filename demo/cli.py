import logging
import time
import kirei as kr
from kirei import types as krtp

app = kr.CliApplication()

logging.basicConfig(level=logging.DEBUG)


@app.register()
def echo(msg):
    return msg


@app.register()
def add(a: int, b: int):
    return a + b


@app.register()
def long_time_operation():
    time.sleep(5)


@app.register()
def div(a: int, b: int):
    return a / b


@app.register()
def file_test(f: krtp.UserInputFilePath):
    print(f)


@app.register()
def csv_to_xlsx(f: krtp.UserInputFilePath) -> krtp.UserOutputFilePath:
    return krtp.UserOutputFilePath(f)


if __name__ == "__main__":
    app()
