# KiRei

Kirei is a typed, multi-backend user interface framework. 
You can easily add an (or multiple, if you want!) user interface to your script.


## Quick Start

```python
import kirei as kr

app = kr.CliApplication()

@app.register()
def echo(msg):  # no type hint will assumed your input are `str` type, and parse your output as str type
    return msg


if __name__ == "__main__":
    app()
```

