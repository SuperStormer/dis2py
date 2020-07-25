# dis2py

converts dis.dis output into python source code

## Example Usage

```python
>>> from dis2py import pretty_decompile
>>> with open("samples/disas.txt") as f:
...     print(pretty_decompile(f.read()))
...
def a(s):
    o=([0])*len(s)
    for (i,c) in enumerate(s):
        o[i]=(c*2)-60
    return o
def b(s,t):
    for (x,y) in zip(s,t):
        yield (x+y)-50
    return None
def c(s):
    return listcomp_0x7ff31a16f0e0(iter(s))
def listcomp_0x7ff31a16f0e0(__0):
    __temp=[]
    for c in __0:
        __temp.append(c+5)
    return __temp
def e(s):
    s=listcomp_0x7ff31a16f240(iter(s))
    o=listcomp_0x7ff31a16f2f0(iter(b(a(s),c(s))))
    return bytes(o)
def listcomp_0x7ff31a16f240(__0):
    __temp=[]
    for c in __0:
        __temp.append(ord(c))
    return __temp
def listcomp_0x7ff31a16f2f0(__0):
    __temp=[]
    for c in __0:
        __temp.append((c^5)-30)
    return __temp
def main():
    s=input('Guess?')
    o=b'\xae\xc0\xa1\xab\xef\x15\xd8\xca\x18\xc6\xab\x17\x93\xa8\x11\xd7\x18\x15\xd7\x17\xbd\x9a\xc0\xe9\x93\x11\xa7\x04\xa1\x1c\x1c\xed'
    if e(s)==o:
        print('Correct!')
    else:
        print('Wrong...')
    return None
```
