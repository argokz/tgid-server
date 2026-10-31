
def r_get(r, col, def_val):
    if type(r) is dict:
        return r.get(col.lower(), r.get(col, def_val))
    try:
        return r[col]
    except:
        return ''
