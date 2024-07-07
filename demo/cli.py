import time
import kirei as kr

app = kr.CliApplication()


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


if __name__ == "__main__":
    app()
