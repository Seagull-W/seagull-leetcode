"""Deterministic small-input fixtures using independent exhaustive oracles.

Run from repo root: python tests/generate_cases.py
Expectations are checked against Python references before writing the fixture.
"""
from functools import lru_cache
import itertools as it
import json
import math
from pathlib import Path
import random
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from content.catalog import PROBLEMS
from judge import equal

rng=random.Random(20261005)
def arr(lo=-3,hi=5,n=None):return [rng.randint(lo,hi) for _ in range(rng.randint(0,7) if n is None else n)]
def word(alphabet='abc',n=None):return ''.join(rng.choice(alphabet) for _ in range(rng.randint(0,7) if n is None else n))
def subsets(a):return [list(s) for k in range(len(a)+1) for s in it.combinations(a,k)]
def path(nexts,head):
    out=[]
    while head!=-1 and head not in out:out.append(head);head=nexts[head]
    return out
def uf(n,edges):
    parent=list(range(n))
    def find(x):
        while parent[x]!=x:x=parent[x]
        return x
    for u,v in edges:parent[find(u)]=find(v)
    return [find(x) for x in range(n)]
def grid_paths(g):
    def walk(i,j):
        if i==len(g)-1 and j==len(g[0])-1:return [g[i][j]]
        out=[]
        if i+1<len(g):out += [g[i][j]+v for v in walk(i+1,j)]
        if j+1<len(g[0]):out += [g[i][j]+v for v in walk(i,j+1)]
        return out
    return walk(0,0)

def inputs(i):
    if i==1:return [sorted(arr())]
    if i in (2,3,6,9,10,11,21,33,49,54,55):
        a=arr(0,5) if i in (21,49) else arr(1,5) if i==54 else arr(-3,3)
        if i==11:return [a,rng.randint(-3,4)]
        if i==33:return [a,rng.randint(0,len(a))]
        return [a]
    if i==4:return [sorted(arr()),sorted(arr())]
    if i==5:return [word('abcABC012 !?')]
    if i in (7,12):
        while True:
            a=arr();a=sorted(a) if i==12 else a;t=rng.randint(-4,8)
            if sum(a[u]+a[v]==t for u in range(len(a)) for v in range(u+1,len(a)))<=1:return [a,t]
    if i==8:return [word(),word()]
    if i in (13,56,57,61):return [word()] if i in (13,61) else [word(),word()]
    if i==14:return [arr(1,5),rng.randint(1,15)]
    if i in (15,23,32):
        a=arr(n=rng.randint(1,7));return [a,rng.randint(1,len(a))]
    if i in (16,17):return [sorted(set(arr())) if i==16 else sorted(arr()),rng.randint(-4,8)]
    if i==18:return [rng.randint(0,10**12)]
    if i==19:
        a=sorted(rng.sample(range(-10,11),rng.randint(1,8)));k=rng.randrange(len(a));return [a[k:]+a[:k]]
    if i==20:return [word('()[]{}')]
    if i==22:
        a,b,c=[rng.randint(-8,8) for _ in range(3)];return [[str(a),str(b),rng.choice('+-*'),str(c),rng.choice('+-*')]]
    if i in (24,25,26,27):
        n=rng.randint(0,7);order=list(range(n));rng.shuffle(order);links=[-1]*n
        for a,b in zip(order,order[1:]):links[a]=b
        head=order[0] if n else -1
        if i==26 and n and rng.choice([True,False]):links[order[-1]]=rng.choice(order)
        return [arr(n=n),links,head] if i==24 else [links,head]
    if i in (28,29,30,31):
        t=arr(0,9,n=rng.choice([0,1,3,7,15,31]))
        for j in range(1,len(t)):
            if t[(j-1)//2]==-1 or rng.randrange(4)==0:t[j]=-1
        return [t,rng.randint(0,25)] if i==31 else [t]
    if i==34:return [arr(1,6,n=rng.randint(0,6))]
    if i==35:
        rows,cols=rng.randint(0,4),rng.randint(1,5)
        return [[[rng.randint(0,1) for _ in range(cols)] for _ in range(rows)]]
    if i in (36,37,38):
        n=rng.randint(1,6) if i==36 else rng.randint(0,6)
        e=[[u,v] for u in range(n) for v in range(n) if rng.randrange(5)==0 and (i==38 or u<=v)]
        return [n,e,rng.randrange(n),rng.randrange(n)] if i==36 else [n,e]
    if i in (39,40):return [rng.sample(range(-5,8),rng.randint(0,6))]
    if i==41:return [rng.randint(0,4)]
    if i==42:return [rng.sample(range(1,12),rng.randint(0,7)),rng.randint(0,20)]
    if i==43:return [arr(0,9)]
    if i==44:return [arr(0,5,n=rng.randint(1,8))]
    if i in (45,46):
        edges=[]
        for _ in range(rng.randint(0,7)):
            a=rng.randint(-4,4);edges.append([a,a+rng.randint(1 if i==45 else 0,5)])
        return [edges]
    if i==47:return [arr(1,5,n=rng.randint(0,5)),arr(1,5,n=rng.randint(0,5))]
    if i==48:return [rng.randint(0,20)]
    if i==50:return [arr(n=rng.randint(1,7))]
    if i in (51,52):return [rng.sample(range(1,7),rng.randint(0,4)),rng.randint(0,15)]
    if i==53:
        n=rng.randint(0,7);return [arr(1,5,n),arr(0,9,n),rng.randint(0,12)]
    if i==58:return [rng.randint(1,8),rng.randint(1,8)]
    if i==59:return [[[rng.randint(0,8) for _ in range(4)] for _ in range(rng.randint(1,4))]]
    if i==60:return [word(),sorted({word(n=rng.randint(1,3)) for _ in range(7)})]
    if i==62:return [word('0123456789',rng.randint(1,9))]
    if i==63:return [rng.randint(0,100)]
    raise AssertionError(i)

def oracle(i,args):
    a=args[0]
    if i==1:return sorted(set(a))
    if i==2:return [x for x in a if x]+[0]*a.count(0)
    if i==3:return [sum(a[:j+1]) for j in range(len(a))]
    if i==4:return sorted(a+args[1])
    if i==5:
        s=re.sub('[^a-z0-9]','',a.lower());return s==s[::-1]
    if i==6:return [math.prod(a[:j]+a[j+1:]) for j in range(len(a))]
    if i in (7,12):return next(([u,v] for u in range(len(a)) for v in range(u+1,len(a)) if a[u]+a[v]==args[1]),[])
    if i==8:return sorted(a)==sorted(args[1])
    if i==9:return any(a[u]==a[v] for u in range(len(a)) for v in range(u+1,len(a)))
    if i==10:
        best=0
        for x in a:
            length=0
            while x+length in a:length+=1
            best=max(best,length)
        return best
    if i==11:return sum(sum(a[l:r])==args[1] for l in range(len(a)) for r in range(l+1,len(a)+1))
    if i==13:return max((r-l for l in range(len(a)+1) for r in range(l,len(a)+1) if len(set(a[l:r]))==r-l),default=0)
    if i==14:return min((r-l for l in range(len(a)) for r in range(l+1,len(a)+1) if sum(a[l:r])>=args[1]),default=0)
    if i==15:return max(sum(a[j:j+args[1]]) for j in range(len(a)-args[1]+1))
    if i==16:return a.index(args[1]) if args[1] in a else -1
    if i==17:return next((j for j,x in enumerate(a) if x>=args[1]),len(a))
    if i==18:return math.isqrt(a)
    if i==19:return min(a)
    if i==20:
        old=None
        while old!=a:old=a;a=a.replace('()','').replace('[]','').replace('{}','')
        return not a
    if i==21:return [next((x for x in a[j+1:] if x>a[j]),-1) for j in range(len(a))]
    if i==22:
        x,y,op,z,op2=a
        return eval(f'({int(x)}{op}{int(y)}){op2}{int(z)}',{'__builtins__':{}})
    if i==23:return [max(a[j:j+args[1]]) for j in range(len(a)-args[1]+1)]
    if i==24:return [a[j] for j in path(args[1],args[2])]
    if i==25:
        order=path(a,args[1]);out=[-1]*len(a)
        for j in range(1,len(order)):out[order[j]]=order[j-1]
        return [order[-1] if order else -1]+out
    if i==26:
        seen=set();p=args[1]
        while p!=-1:
            if p in seen:return True
            seen.add(p);p=a[p]
        return False
    if i==27:
        order=path(a,args[1]);return order[len(order)//2] if order else -1
    if i==28:return max(((j+1).bit_length() for j,x in enumerate(a) if x!=-1),default=0)
    if i==29:
        stack=[];p=0;out=[]
        while stack or (p<len(a) and a[p]!=-1):
            while p<len(a) and a[p]!=-1:stack.append(p);p=2*p+1
            p=stack.pop();out.append(a[p]);p=2*p+2
        return out
    if i==30:
        rows=[]
        for d in range(max(0,len(a).bit_length())):
            row=[x for x in a[2**d-1:2**(d+1)-1] if x!=-1]
            if row:rows.append(row)
        return rows
    if i==31:
        for j,x in enumerate(a):
            if x==-1 or any(k<len(a) and a[k]!=-1 for k in (2*j+1,2*j+2)):continue
            total=0;p=j
            while True:
                total+=a[p]
                if p==0:break
                p=(p-1)//2
            if total==args[1]:return True
        return False
    if i==32:return sorted(a,reverse=True)[args[1]-1]
    if i==33:return sorted(a)[:args[1]]
    if i==34:
        @lru_cache(None)
        def f(t):
            if len(t)<2:return 0
            return min(t[u]+t[v]+f(tuple(sorted([t[j] for j in range(len(t)) if j not in (u,v)]+[t[u]+t[v]]))) for u in range(len(t)) for v in range(u+1,len(t)))
        return f(tuple(sorted(a)))
    if i==35:
        if not a:return 0
        cols=len(a[0]);e=[];land=set()
        for r,row in enumerate(a):
            for c,x in enumerate(row):
                if x!=1:continue
                u=r*cols+c;land.add(u)
                for dr,dc in ((1,0),(0,1)):
                    rr,cc=r+dr,c+dc
                    if rr<len(a) and cc<cols and a[rr][cc]==1:e.append((u,rr*cols+cc))
        groups=uf(len(a)*cols,e);return len({groups[j] for j in land})
    if i==36:
        n,e,s,t=args;d=[[0 if u==v else 999 for v in range(n)] for u in range(n)]
        for u,v in e:
            if u!=v:d[u][v]=d[v][u]=1
        for k in range(n):
            for u in range(n):
                for v in range(n):d[u][v]=min(d[u][v],d[u][k]+d[k][v])
        return -1 if d[s][t]==999 else d[s][t]
    if i==37:return len(set(uf(a,args[1])))
    if i==38:
        n,e=args;g=[[] for _ in range(n)];color=[0]*n
        for course,before in e:g[before].append(course)
        def dfs(u):
            if color[u]==1:return False
            if color[u]==2:return True
            color[u]=1
            if any(not dfs(v) for v in g[u]):return False
            color[u]=2;return True
        return all(dfs(u) for u in range(n))
    if i==39:return subsets(a)
    if i==40:return [list(x) for x in it.permutations(a)]
    if i==41:
        out=[]
        for chars in it.product('()',repeat=2*a):
            balance=0;valid=True
            for c in chars:
                balance+=1 if c=='(' else -1
                if balance<0:valid=False;break
            if valid and balance==0:out.append(''.join(chars))
        return out
    if i==42:return [sorted(s) for s in subsets(a) if sum(s)==args[1]]
    if i==43:return max([0]+[a[v]-a[u] for u in range(len(a)) for v in range(u+1,len(a))])
    if i==44:
        seen={0};q=[0]
        for u in q:
            for v in range(u+1,min(len(a),u+a[u]+1)):
                if v not in seen:seen.add(v);q.append(v)
        return len(a)-1 in seen
    if i==45:
        best=0
        for s in subsets(a):
            s=sorted(s)
            if all(s[j][1]<=s[j+1][0] for j in range(len(s)-1)):best=max(best,len(s))
        return best
    if i==46:
        e=[(u,v) for u in range(len(a)) for v in range(u+1,len(a)) if max(a[u][0],a[v][0])<=min(a[u][1],a[v][1])]
        groups=uf(len(a),e);return sorted([[min(a[j][0] for j in range(len(a)) if groups[j]==g),max(a[j][1] for j in range(len(a)) if groups[j]==g)] for g in set(groups)])
    if i==47:
        cookies=args[1]
        def assign(j,used):
            if j==len(a):return 0
            return max([assign(j+1,used)]+[1+assign(j+1,used|{k}) for k,x in enumerate(cookies) if k not in used and x>=a[j]])
        return assign(0,set())
    if i==48:
        @lru_cache(None)
        def f(n):return 1 if n<=1 else f(n-1)+f(n-2)
        return f(a)
    if i==49:return max([0]+[sum(a[j] for j in selected) for selected in subsets(list(range(len(a)))) if all(v-u>1 for u,v in zip(selected,selected[1:]))])
    if i==50:return max(sum(a[l:r]) for l in range(len(a)) for r in range(l+1,len(a)+1))
    if i in (51,63):
        amount=args[1] if i==51 else a;coins=a if i==51 else [x*x for x in range(1,math.isqrt(a)+1)]
        q=[(0,0)];seen={0}
        for s,d in q:
            if s==amount:return d
            for c in coins:
                if s+c<=amount and s+c not in seen:seen.add(s+c);q.append((s+c,d+1))
        return -1
    if i==52:
        amount=args[1]
        return sum(sum(c*k for c,k in zip(a,counts))==amount for counts in it.product(*(range(amount//c+1) for c in a)))
    if i==53:
        w,v,c=args;return max([0]+[sum(v[j] for j in s) for s in subsets(list(range(len(w)))) if sum(w[j] for j in s)<=c])
    if i==54:return any(2*sum(s)==sum(a) for s in subsets(a))
    if i==55:return max((len(s) for s in subsets(a) if all(x<y for x,y in zip(s,s[1:]))),default=0)
    if i==56:
        def is_sub(s,b):
            iterator=iter(b);return all(any(x==y for y in iterator) for x in s)
        return max(len(s) for s in subsets(a) if is_sub(s,args[1]))
    if i==57:
        b=args[1]
        @lru_cache(None)
        def dist(u,v):
            if u==len(a):return len(b)-v
            if v==len(b):return len(a)-u
            if a[u]==b[v]:return dist(u+1,v+1)
            return 1+min(dist(u+1,v),dist(u,v+1),dist(u+1,v+1))
        return dist(0,0)
    if i==58:return math.comb(a+args[1]-2,a-1)
    if i==59:return min(grid_paths(a))
    if i==60:
        words=args[1]
        @lru_cache(None)
        def f(s):return not s or any(s.startswith(w) and f(s[len(w):]) for w in words)
        return f(a)
    if i==61:return max(len(s) for s in subsets(a) if s==s[::-1])
    if i==62:
        @lru_cache(None)
        def f(s):
            if not s:return 1
            if s[0]=='0':return 0
            return f(s[1:])+(f(s[2:]) if len(s)>=2 and 10<=int(s[:2])<=26 else 0)
        return f(a)
    raise AssertionError(i)

def main():
    fixtures={};count=0
    for p in PROBLEMS:
        namespace={};exec(p['solutions']['python'],namespace);cases=[]
        for _ in range(16):
            args=inputs(p['number']);expected=oracle(p['number'],args)
            actual=namespace['solve'](*json.loads(json.dumps(args)))
            if not equal(actual,expected,p['unordered']):raise AssertionError((p['id'],args,expected,actual))
            cases.append(dict(input=args,expected=expected));count+=1
        fixtures[p['id']]=cases
    target=Path(__file__).resolve().parents[1]/'content'/'extra_cases.json'
    text='{\n'+',\n'.join('  '+json.dumps(pid)+': [\n'+',\n'.join('    '+json.dumps(c,ensure_ascii=False,separators=(',',':')) for c in cases)+'\n  ]' for pid,cases in fixtures.items())+'\n}\n'
    target.write_text(text,encoding='utf-8')
    print(f'Generated and independently checked {count} cases for {len(fixtures)} exercises.')

if __name__=='__main__':main()
