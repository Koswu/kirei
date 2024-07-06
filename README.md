# KiRei

kirei is a typed, multi-backend user interface framework. 
you can easy to add user interface to your script.


## Quick Start

```python
import kirei as kr

app = kr.CliApplication()

@app.register()
def echo(msg):  # no type hint will assume your input and output are `str` type
    return msg


if __name__ == "__main__":
    app()
```

