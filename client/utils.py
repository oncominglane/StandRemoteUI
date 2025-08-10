def make_focusable_scale(scale, var, step=1.0):
    def on_click(event):
        global active_scale
        active_scale = (scale, var, step)
        scale.focus_set()
    scale.bind("<Button-1>", on_click)

def on_arrow_key(event):
    global active_scale
    if active_scale is None:
        return
    scale, var, step = active_scale
    value = var.get()
    if event.keysym == "Up":
        var.set(value + step)
    elif event.keysym == "Down":
        var.set(value - step)