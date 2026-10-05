"""Original bilingual exercises. Test expectations are explicit, not computed by judge."""
import textwrap

PROBLEMS = []

def add(title, topic, level, description, args, result, cases, py, rs, approach,
        complexity, pitfalls, hints=None, unordered=False):
    number = len(PROBLEMS) + 1
    py = textwrap.dedent(py).strip() + '\n'
    rs = textwrap.dedent(rs).strip() + '\n'
    params = ', '.join(name for name, _ in args)
    rustparams = ', '.join(f'{name}: {kind}' for name, kind in args)
    PROBLEMS.append(dict(id=f'a{number:02}', number=number, title=title, topic=topic,
        difficulty=level, version=1, description=description,
        args=args, result_type=result, cases=[dict(input=i, expected=e) for i,e in cases],
        templates={'python': f'def solve({params}):\n    # 在这里实现；返回结果，不要读取标准输入。\n    raise NotImplementedError\n',
                   'rust': f'pub fn solve({rustparams}) -> {result} {{\n    // 在这里实现；返回结果，不要定义 main。\n    todo!()\n}}\n'},
        solutions={'python':py, 'rust':rs}, approach=approach, complexity=complexity,
        pitfalls=pitfalls, hints=hints or ['先用一个小例子手工推演，明确需要维护的信息。', approach.split('。')[0]+'。'],
        unordered=unordered))

V = 'Vec<i64>'
S = 'String'
N = 'i64'
B = 'bool'

# 数组与字符串：每个用例为 (位置参数列表, 期望结果)。
add('有序数组去重', '数组与字符串', '基础',
    '给定非递减整数数组 nums，返回保留第一次出现后的新数组。允许创建新数组，不要求原地修改。长度 0～10000；元素绝对值不超过 10⁶。',
    [('nums',V)], V, [([[]],[]),([[1,1,2,2,3]],[1,2,3]),([[-2,-2,0,4,4]],[-2,0,4]),([[7]],[7])],
    '''
    def solve(nums):
        out = []
        for x in nums:
            if not out or out[-1] != x:
                out.append(x)
        return out
    ''', '''
    pub fn solve(nums: Vec<i64>) -> Vec<i64> {
        let mut out = Vec::new();
        for x in nums { if out.last() != Some(&x) { out.push(x); } }
        out
    }
    ''', '排序保证相同值连续。遍历时只比较输出末尾；输出始终是已扫描前缀的去重结果。',
    '时间 O(n)，额外空间 O(n)。', '空数组不能直接访问首元素；这一做法依赖输入已经排序。')

add('把零移到末尾', '数组与字符串', '基础',
    '返回 nums 的新排列：非零元素保持相对顺序，所有零放到末尾。长度 0～10000，元素绝对值不超过 10⁶。',
    [('nums',V)],V,[([[]],[]),([[0,1,0,3,12]],[1,3,12,0,0]),([[0,0]],[0,0]),([[-1,0,2]],[-1,2,0])],
    '''
    def solve(nums):
        out = [x for x in nums if x != 0]
        return out + [0] * (len(nums) - len(out))
    ''','''
    pub fn solve(nums: Vec<i64>) -> Vec<i64> {
        let n = nums.len();
        let mut out: Vec<i64> = nums.into_iter().filter(|&x| x != 0).collect();
        out.resize(n, 0); out
    }
    ''','稳定筛出非零元素，再补齐长度。若要求原地，可用写指针覆盖非零前缀，再把余下位置置零。',
    '时间 O(n)，本题新数组空间 O(n)；原地变体 O(1)。','不能用排序：排序会改变非零元素的相对顺序。')

add('每个位置的前缀和', '数组与字符串', '基础',
    '返回数组 out，out[i] 为 nums[0] 到 nums[i] 的总和。空输入返回空数组。长度不超过 10000，元素绝对值不超过 10⁶。',
    [('nums',V)],V,[([[]],[]),([[1,2,3]],[1,3,6]),([[-2,3,-1]],[-2,1,0]),([[0,0]],[0,0])],
    '''
    def solve(nums):
        total = 0
        out = []
        for x in nums:
            total += x
            out.append(total)
        return out
    ''','''
    pub fn solve(nums: Vec<i64>) -> Vec<i64> {
        let mut total = 0; nums.into_iter().map(|x| {total += x; total}).collect()
    }
    ''','维护已扫描元素的总和，每次加入当前元素再记录。区间求和变体可设置长度 n+1 的前缀表。',
    '时间 O(n)，输出空间 O(n)。','Rust 使用 i64 避免前缀总和超出 i32。')

add('合并两份有序数组', '数组与字符串', '基础',
    'a 与 b 均为非递减整数数组，返回合并后的非递减数组，保留重复值。每份长度不超过 5000。',
    [('a',V),('b',V)],V,[([[],[]],[]),([[1,3],[2,4]],[1,2,3,4]),([[],[0]],[0]),([[-2,2,2],[-2,3]],[-2,-2,2,2,3])],
    '''
    def solve(a, b):
        i = j = 0
        out = []
        while i < len(a) and j < len(b):
            if a[i] <= b[j]:
                out.append(a[i]); i += 1
            else:
                out.append(b[j]); j += 1
        return out + a[i:] + b[j:]
    ''','''
    pub fn solve(a: Vec<i64>, b: Vec<i64>) -> Vec<i64> {
        let (mut i,mut j)=(0,0); let mut out=Vec::new();
        while i<a.len() && j<b.len() {
            if a[i]<=b[j] {out.push(a[i]);i+=1;} else {out.push(b[j]);j+=1;}
        }
        out.extend_from_slice(&a[i..]); out.extend_from_slice(&b[j..]); out
    }
    ''','两份数组各有一个指针，每次取较小的当前元素。一份用尽后另一份剩余部分已经有序。',
    '时间 O(n+m)，输出空间 O(n+m)。','两边相等时也要推进一个指针；循环结束后记得追加剩余元素。')

add('忽略符号的回文', '数组与字符串', '基础',
    '输入 ASCII 字符串 text，只保留字母和数字并忽略大小写，判断是否回文。空串或过滤后为空均为 true。长度不超过 10000。',
    [('text',S)],B,[(['A man, a plan, a canal: Panama'],True),(['race a car'],False),(['!!!'],True),(['0P'],False)],
    '''
    def solve(text):
        s = ''.join(c.lower() for c in text if c.isalnum())
        return s == s[::-1]
    ''','''
    pub fn solve(text: String) -> bool {
        let s: Vec<u8> = text.bytes().filter(|c| c.is_ascii_alphanumeric()).map(|c|c.to_ascii_lowercase()).collect();
        s.iter().eq(s.iter().rev())
    }
    ''','先统一字符规则，再检查镜像位置。可以进一步直接使用两端指针跳过符号。',
    '时间 O(n)，本实现空间 O(n)；双指针变体 O(1)。','本题规定 ASCII。Python isalnum 对 Unicode 的行为更宽，不能直接推广为所有语言完全一致。')

add('除自身以外的乘积', '数组与字符串', '进阶',
    'out[i] 等于 nums 中除 nums[i] 外所有元素的乘积。禁止除法。空输入返回 []，单元素返回 [1]。长度不超过 30，保证每个前缀、后缀及答案乘积均在 i64 范围内。',
    [('nums',V)],V,[([[]],[]),([[7]],[1]),([[1,2,3,4]],[24,12,8,6]),([[0,2,0]],[0,0,0]),([[-1,0,3]],[0,-3,0])],
    '''
    def solve(nums):
        out = [1] * len(nums)
        prefix = 1
        for i, x in enumerate(nums):
            out[i] = prefix
            prefix *= x
        suffix = 1
        for i in range(len(nums)-1, -1, -1):
            out[i] *= suffix
            suffix *= nums[i]
        return out
    ''','''
    pub fn solve(nums: Vec<i64>) -> Vec<i64> {
        let mut out=vec![1;nums.len()];let mut p=1;
        for i in 0..nums.len(){out[i]=p;p*=nums[i];}
        p=1;for i in (0..nums.len()).rev(){out[i]*=p;p*=nums[i];} out
    }
    ''','把答案拆成左侧乘积与右侧乘积。先存左侧前缀，反向遍历再乘右侧后缀，不需要除法，也自然处理零。',
    '时间 O(n)，除输出外空间 O(1)。','前缀和后缀都不包含当前位置；多个零不能采用总乘积再除的方法。')

add('两个数的下标', '哈希表', '基础',
    '寻找 nums 中和为 target 的两个不同下标。保证至多有一对答案，返回较小下标在前的数组；不存在返回 []。长度不超过 10000，元素及 target 绝对值不超过 10⁶。',
    [('nums',V),('target',N)],V,[([[2,7,11,15],9],[0,1]),([[3,3],6],[0,1]),([[1,2],8],[]),([[],0],[])],
    '''
    def solve(nums, target):
        seen = {}
        for i, x in enumerate(nums):
            if target-x in seen:
                return [seen[target-x], i]
            seen[x] = i
        return []
    ''','''
    pub fn solve(nums: Vec<i64>, target: i64) -> Vec<i64> {
        let mut seen=std::collections::HashMap::new();
        for (i,x) in nums.into_iter().enumerate(){
            if let Some(&j)=seen.get(&(target-x)){return vec![j,i as i64];}
            seen.insert(x,i as i64);
        } vec![]
    }
    ''','遍历 x 时查找 target-x 是否已出现。先查再插入，确保不会使用同一个位置两次。',
    '平均时间 O(n)，空间 O(n)。','值相同也可以构成答案，但下标必须不同。')

add('相同字母的两段文本', '哈希表', '基础',
    'a、b 只含小写英文字母，判断两者每个字母的出现次数是否相同。长度分别不超过 10000。',
    [('a',S),('b',S)],B,[(['anagram','nagaram'],True),(['rat','car'],False),(['',''],True),(['aa','a'],False)],
    '''
    def solve(a, b):
        from collections import Counter
        return Counter(a) == Counter(b)
    ''','''
    pub fn solve(a: String,b: String)->bool{
        let mut counts=[0i64;26];for c in a.bytes(){counts[(c-b'a')as usize]+=1;}
        for c in b.bytes(){counts[(c-b'a')as usize]-=1;}counts.iter().all(|&x|x==0)
    }
    ''','字母顺序不影响答案，因此把字符串转换为频次表。比较频次，或使用一加一减的计数表。',
    '时间 O(n+m)，固定字母表空间 O(1)。','集合只记录是否出现，无法区分重复次数。')

add('是否出现重复数字', '哈希表', '基础',
    '判断 nums 中是否存在出现至少两次的整数。长度 0～10000，元素绝对值不超过 10⁶。',
    [('nums',V)],B,[([[]],False),([[1,2,3]],False),([[1,2,1]],True),([[0,0]],True)],
    '''
    def solve(nums):
        seen = set()
        for x in nums:
            if x in seen:
                return True
            seen.add(x)
        return False
    ''','''
    pub fn solve(nums: Vec<i64>)->bool{
        let mut s=std::collections::HashSet::new();for x in nums{if !s.insert(x){return true;}}false
    }
    ''','集合保存已经出现的值，插入失败或查询命中就说明重复。',
    '平均时间 O(n)，空间 O(n)。','不要用两层枚举完成本可线性解决的问题。')

add('最长连续整数段', '哈希表', '进阶',
    '返回 nums 中可组成的最长连续整数段长度，不要求在原数组中相邻。重复值不增加长度。长度不超过 10000，元素绝对值不超过 10⁶。',
    [('nums',V)],N,[([[]],0),([[100,4,200,1,3,2]],4),([[1,2,2,3]],3),([[-2,-1,1]],2)],
    '''
    def solve(nums):
        values = set(nums)
        best = 0
        for x in values:
            if x-1 not in values:
                y = x
                while y in values:
                    y += 1
                best = max(best, y-x)
        return best
    ''','''
    pub fn solve(nums: Vec<i64>)->i64{
        let s:std::collections::HashSet<i64>=nums.into_iter().collect();let mut best=0;
        for &x in &s{if !s.contains(&(x-1)){let mut y=x;while s.contains(&y){y+=1;}best=best.max(y-x);}}best
    }
    ''','只有不存在前驱 x-1 的数字才是连续段起点。从每个起点向后扩展，每个不同数字至多被扩展一次。',
    '平均时间 O(n)，空间 O(n)。','从所有数字都向后扩展会在长连续段上退化为 O(n²)。')

add('和为目标的子数组个数', '哈希表', '进阶',
    '返回连续非空子数组中，元素和为 target 的个数。nums 可以包含负数和零。长度不超过 10000，元素及 target 绝对值不超过 10⁶。',
    [('nums',V),('target',N)],N,[([[1,1,1],2],2),([[1,-1,0],0],3),([[],0],0),([[0,0,0],0],6)],
    '''
    def solve(nums, target):
        counts = {0: 1}
        total = answer = 0
        for x in nums:
            total += x
            answer += counts.get(total-target, 0)
            counts[total] = counts.get(total, 0) + 1
        return answer
    ''','''
    pub fn solve(nums:Vec<i64>,target:i64)->i64{
        let mut counts=std::collections::HashMap::from([(0i64,1i64)]);let(mut sum,mut ans)=(0,0);
        for x in nums{sum+=x;ans+=counts.get(&(sum-target)).copied().unwrap_or(0);*counts.entry(sum).or_insert(0)+=1;}ans
    }
    ''','区间和等于两个前缀和的差。到当前前缀 s 时，统计此前 s-target 出现次数；初始空前缀为 0，出现一次。',
    '平均时间 O(n)，空间 O(n)。','必须先查询再登记当前前缀，否则 target=0 会多算空区间；有负数时普通滑动窗口无效。')

add('有序数组中的一对和', '双指针与窗口', '基础',
    'nums 非递减，找两个不同位置使和为 target。保证至多一个答案，返回零基下标，较小在前；无解返回 []。长度不超过 10000。',
    [('nums',V),('target',N)],V,[([[2,7,11,15],9],[0,1]),([[-3,1,2,5],2],[0,3]),([[1,1],2],[0,1]),([[],4],[])],
    '''
    def solve(nums, target):
        l, r = 0, len(nums)-1
        while l < r:
            s = nums[l]+nums[r]
            if s == target: return [l, r]
            if s < target: l += 1
            else: r -= 1
        return []
    ''','''
    pub fn solve(nums:Vec<i64>,target:i64)->Vec<i64>{
        if nums.len()<2{return vec![];}let(mut l,mut r)=(0,nums.len()-1);
        while l<r{let s=nums[l]+nums[r];if s==target{return vec![l as i64,r as i64];}
        if s<target{l+=1;}else{r-=1;}}vec![]
    }
    ''','两端指针的和偏小时左指针右移，偏大时右指针左移。排序使被丢弃的位置不可能组成答案。',
    '时间 O(n)，空间 O(1)。','Rust 空数组的 len()-1 会下溢，先判断长度。')

add('最长无重复字符窗口', '双指针与窗口', '进阶',
    '返回 text 中不含重复字符的最长连续子串长度。本题按 ASCII 字符计算；长度不超过 10000。',
    [('text',S)],N,[(['abcabcbb'],3),(['bbbbb'],1),(['pwwkew'],3),([''],0),(['abba'],2)],
    '''
    def solve(text):
        last = {}
        left = best = 0
        for right, c in enumerate(text):
            left = max(left, last.get(c, -1)+1)
            last[c] = right
            best = max(best, right-left+1)
        return best
    ''','''
    pub fn solve(text:String)->i64{
        let mut last=std::collections::HashMap::new();let(mut l,mut best)=(0usize,0usize);
        for(r,c)in text.bytes().enumerate(){if let Some(&p)=last.get(&c){l=l.max(p+1);}last.insert(c,r);best=best.max(r-l+1);}best as i64
    }
    ''','维护无重复窗口 [left,right]。记录字符上次位置，重复时 left 跳到该位置后面，但不能倒退。',
    '平均时间 O(n)，空间 O(字符表大小)。','abba 是左边界不能倒退的反例；子串必须连续。')

add('达到阈值的最短窗口', '双指针与窗口', '进阶',
    'nums 只含正整数，target 为正整数。返回和至少为 target 的最短连续子数组长度，无解返回 0。长度不超过 10000，数字与 target 不超过 10⁶。',
    [('nums',V),('target',N)],N,[([[2,3,1,2,4,3],7],2),([[1,2],9],0),([[],1],0),([[4,1],4],1)],
    '''
    def solve(nums, target):
        l = total = 0
        best = len(nums)+1
        for r, x in enumerate(nums):
            total += x
            while total >= target:
                best = min(best, r-l+1)
                total -= nums[l]; l += 1
        return 0 if best > len(nums) else best
    ''','''
    pub fn solve(nums:Vec<i64>,target:i64)->i64{
        let(mut l,mut s,mut best)=(0usize,0i64,nums.len()+1);
        for r in 0..nums.len(){s+=nums[r];while s>=target{best=best.min(r-l+1);s-=nums[l];l+=1;}}
        if best>nums.len(){0}else{best as i64}
    }
    ''','正数保证右扩使和增加、左缩使和减少。每次达到阈值后尽量缩小窗口并更新最短长度。',
    '时间 O(n)，空间 O(1)。','若允许负数，和不再单调，这个算法不能直接使用。')

add('固定窗口的最大总和', '双指针与窗口', '基础',
    '返回 nums 中长度恰好为 k 的连续子数组最大和。保证 1≤k≤len(nums)≤10000，元素绝对值不超过 10⁶。',
    [('nums',V),('k',N)],N,[([[1,4,-2,3],2],5),([[-5,-2,-3],2],-5),([[7],1],7),([[1,2,3],3],6)],
    '''
    def solve(nums, k):
        total = sum(nums[:k])
        best = total
        for r in range(k, len(nums)):
            total += nums[r]-nums[r-k]
            best = max(best, total)
        return best
    ''','''
    pub fn solve(nums:Vec<i64>,k:i64)->i64{
        let k=k as usize;let mut s:i64=nums[..k].iter().sum();let mut best=s;
        for r in k..nums.len(){s+=nums[r]-nums[r-k];best=best.max(s);}best
    }
    ''','相邻固定窗口只差一个进入元素和一个离开元素。先算第一个窗口，再增量更新。',
    '时间 O(n)，空间 O(1)。','最大值不能初始化为 0，因为所有窗口和都可能为负。')

add('二分查找位置', '二分查找', '基础',
    'nums 严格递增，返回 target 的下标，不存在返回 -1。长度 0～10000，元素和目标绝对值不超过 10⁶。',
    [('nums',V),('target',N)],N,[([[1,3,5],3],1),([[1,3,5],2],-1),([[],2],-1),([[1],1],0)],
    '''
    def solve(nums, target):
        l, r = 0, len(nums)
        while l < r:
            m = (l+r)//2
            if nums[m] < target: l = m+1
            else: r = m
        return l if l < len(nums) and nums[l] == target else -1
    ''','''
    pub fn solve(nums:Vec<i64>,target:i64)->i64{
        let(mut l,mut r)=(0,nums.len());while l<r{let m=l+(r-l)/2;if nums[m]<target{l=m+1;}else{r=m;}}
        if l<nums.len()&&nums[l]==target{l as i64}else{-1}
    }
    ''','使用半开区间 [l,r)，寻找第一个不小于 target 的位置，再检查是否相等。每次严格缩小候选范围。',
    '时间 O(log n)，空间 O(1)。','统一开闭区间；Rust 用 usize 的半开区间可避免 r=m-1 下溢。')

add('第一个不小于目标的位置', '二分查找', '基础',
    'nums 非递减，返回第一个 ≥target 的下标。若全部更小，返回数组长度。允许重复值，长度不超过 10000。',
    [('nums',V),('target',N)],N,[([[1,2,2,4],2],1),([[1,2],3],2),([[],0],0),([[2,2],1],0)],
    '''
    def solve(nums, target):
        l, r = 0, len(nums)
        while l < r:
            m = (l+r)//2
            if nums[m] < target: l = m+1
            else: r = m
        return l
    ''','''
    pub fn solve(nums:Vec<i64>,target:i64)->i64{
        let(mut l,mut r)=(0,nums.len());while l<r{let m=l+(r-l)/2;if nums[m]<target{l=m+1;}else{r=m;}}l as i64
    }
    ''','不变量：l 左侧均小于目标，r 及其右侧均不小于目标。相等时仍向左搜索，最终得到左边界。',
    '时间 O(log n)，空间 O(1)。','不能找到相等值就立即返回，否则重复元素会得到错误边界。')

add('整数平方根', '二分查找', '进阶',
    '输入 0≤x≤10¹²，返回满足 r²≤x 的最大非负整数 r。不能直接调用平方根函数。',
    [('x',N)],N,[([0],0),([1],1),([8],2),([16],4),([1000000000000],1000000)],
    '''
    def solve(x):
        l, r = 0, min(x, 1000000)+1
        while l < r:
            m = (l+r)//2
            if m*m <= x: l = m+1
            else: r = m
        return l-1
    ''','''
    pub fn solve(x:i64)->i64{
        let(mut l,mut r)=(0,x.min(1_000_000)+1);while l<r{let m=l+(r-l)/2;
        if m*m<=x{l=m+1;}else{r=m;}}l-1
    }
    ''','谓词 r²≤x 随 r 增大从真变假。寻找第一个假位置，再减一。根据约束把上界限制在 1000001，避免乘法溢出。',
    '时间 O(log x)，空间 O(1)。','x=0 也需要覆盖；更宽的整数范围可用除法比较避免平方溢出。')

add('旋转数组中的最小值', '二分查找', '进阶',
    '严格递增数组经过旋转，返回最小元素。数组非空、无重复，长度不超过 10000。未旋转也视为合法。',
    [('nums',V)],N,[([[3,4,5,1,2]],1),([[1,2,3]],1),([[7]],7),([[2,1]],1)],
    '''
    def solve(nums):
        l, r = 0, len(nums)-1
        while l < r:
            m = (l+r)//2
            if nums[m] > nums[r]: l = m+1
            else: r = m
        return nums[l]
    ''','''
    pub fn solve(nums:Vec<i64>)->i64{
        let(mut l,mut r)=(0,nums.len()-1);while l<r{let m=l+(r-l)/2;
        if nums[m]>nums[r]{l=m+1;}else{r=m;}}nums[l]
    }
    ''','比较中点和右端：中点更大，最小值一定在其右；否则中点可能是最小值，保留中点收缩右端。',
    '时间 O(log n)，空间 O(1)。','本题无重复。允许重复时需要额外处理相等，最坏复杂度也会变化。')

add('括号是否配对', '栈与队列', '基础',
    'text 只包含 ()[]{}，判断是否正确嵌套且完全匹配。空串合法，长度不超过 10000。',
    [('text',S)],B,[(['([]{})'],True),(['([)]'],False),([''],True),(['('],False),([']'],False)],
    '''
    def solve(text):
        stack = []
        pairs = {')':'(', ']':'[', '}':'{'}
        for c in text:
            if c in '([{': stack.append(c)
            elif not stack or stack.pop() != pairs[c]: return False
        return not stack
    ''','''
    pub fn solve(text:String)->bool{
        let mut s=Vec::new();for c in text.bytes(){match c{
        b'('|b'['|b'{'=>s.push(c),_=>{let expected=match c{b')'=>b'(',b']'=>b'[',_=>b'{'};
        if s.pop()!=Some(expected){return false;}}}}s.is_empty()
    }
    ''','未匹配左括号入栈。右括号必须匹配最近的左括号，因此使用后进先出的栈。',
    '时间 O(n)，空间 O(n)。','计数相同不足以说明合法，([)] 的嵌套顺序错误。')

add('下一个更大的数', '栈与队列', '进阶',
    '对 nums 每个位置，返回右侧第一个严格更大元素的值，不存在返回 -1。长度不超过 10000，nums 中值非负且不超过 10⁶。',
    [('nums',V)],V,[([[2,1,2,4,3]],[4,2,4,-1,-1]),([[3,3]],[-1,-1]),([[]],[]),([[1,2,3]],[2,3,-1])],
    '''
    def solve(nums):
        out = [-1]*len(nums)
        stack = []
        for i, x in enumerate(nums):
            while stack and nums[stack[-1]] < x:
                out[stack.pop()] = x
            stack.append(i)
        return out
    ''','''
    pub fn solve(nums:Vec<i64>)->Vec<i64>{
        let mut out=vec![-1;nums.len()];let mut s:Vec<usize>=Vec::new();
        for i in 0..nums.len(){while let Some(&j)=s.last(){if nums[j]>=nums[i]{break;}s.pop();out[j]=nums[i];}s.push(i);}out
    }
    ''','栈保存还未找到答案的位置，值保持非递增。新元素更大时弹出栈顶并填答案；每个下标只进出一次。',
    '时间 O(n)，空间 O(n)。','严格更大意味着相等元素不能触发弹栈；栈应存下标以便填写结果。')

add('逆波兰表达式求值', '栈与队列', '进阶',
    'tokens 为合法后缀表达式，运算符为 + - * /。除法向零截断，除数非零。所有中间结果绝对值不超过 10⁹，token 数不超过 1000。',
    [('tokens','Vec<String>')],N,[([["2","1","+","3","*"]],9),([["4","13","5","/","+"]],6),([["-7","3","/"]],-2),([["5"]],5)],
    '''
    def solve(tokens):
        stack = []
        for t in tokens:
            if t not in ('+', '-', '*', '/'):
                stack.append(int(t)); continue
            b, a = stack.pop(), stack.pop()
            if t == '+': v = a+b
            elif t == '-': v = a-b
            elif t == '*': v = a*b
            else: v = (abs(a)//abs(b)) * (-1 if (a<0) != (b<0) else 1)
            stack.append(v)
        return stack[-1]
    ''','''
    pub fn solve(tokens:Vec<String>)->i64{
        let mut s:Vec<i64>=Vec::new();for t in tokens{if let Ok(x)=t.parse::<i64>(){s.push(x);}else{
        let b=s.pop().unwrap();let a=s.pop().unwrap();s.push(match t.as_str(){"+"=>a+b,"-"=>a-b,"*"=>a*b,_=>a/b});}}s[0]
    }
    ''','数字压栈，运算符取出最近两个操作数计算再压回。第一个弹出的是右操作数。',
    '时间 O(n)，空间 O(n)。','Python // 对负数向下取整，与题目向零截断不同；减法和除法注意操作数顺序。')

add('每个滑动窗口的最大值', '栈与队列', '进阶',
    '返回 nums 中每个长度 k 的连续窗口最大值。1≤k≤len(nums)≤10000，元素绝对值不超过 10⁶。',
    [('nums',V),('k',N)],V,[([[1,3,-1,-3,5,3,6,7],3],[3,3,5,5,6,7]),([[2,2,1],2],[2,2]),([[4],1],[4]),([[1,2],2],[2])],
    '''
    def solve(nums, k):
        from collections import deque
        q, out = deque(), []
        for i, x in enumerate(nums):
            while q and q[0] <= i-k: q.popleft()
            while q and nums[q[-1]] <= x: q.pop()
            q.append(i)
            if i >= k-1: out.append(nums[q[0]])
        return out
    ''','''
    pub fn solve(nums:Vec<i64>,k:i64)->Vec<i64>{
        let k=k as usize;let mut q:std::collections::VecDeque<usize>=std::collections::VecDeque::new();let mut out=Vec::new();
        for i in 0..nums.len(){while q.front().is_some_and(|&j|j+k<=i){q.pop_front();}
        while q.back().is_some_and(|&j|nums[j]<=nums[i]){q.pop_back();}q.push_back(i);
        if i+1>=k{out.push(nums[*q.front().unwrap()]);}}out
    }
    ''','双端队列存下标，对应值递减。过期下标从队首删除，被新元素压制的旧候选从队尾删除，队首就是最大值。',
    '时间 O(n)，空间 O(k)。','必须保存下标以判断过期；每个元素最多进队和出队一次，嵌套 while 仍是线性。')

# 链表用 next 下标表表达拓扑，可直接在两种语言中判题。
add('沿链表读取节点', '链表', '基础',
    'values 保存节点值，nexts[i] 为下一个节点下标，-1 表示结束。head=-1 表示空链表。返回从 head 开始的节点值序列。保证数组等长、下标合法且从 head 出发无环；最多 10000 个节点。',
    [('values',V),('nexts',V),('head',N)],V,[([[10,20,30],[2,-1,1],0],[10,30,20]),([[],[],-1],[]),([[5],[-1],0],[5]),([[1,2],[-1,-1],1],[2])],
    '''
    def solve(values, nexts, head):
        out = []
        while head != -1:
            out.append(values[head]); head = nexts[head]
        return out
    ''','''
    pub fn solve(values:Vec<i64>,nexts:Vec<i64>,head:i64)->Vec<i64>{
        let mut p=head;let mut out=Vec::new();while p!=-1{out.push(values[p as usize]);p=nexts[p as usize];}out
    }
    ''','节点的物理位置与链表顺序不同，必须沿 next 关系访问。下标表与指针节点表达同一种拓扑。',
    '时间 O(可达节点数)，输出空间 O(可达节点数)。','不能直接返回 values；不要把 -1 转为 usize 后再访问。')

add('反转链表的连接关系', '链表', '进阶',
    'nexts 描述一条包含所有节点、无环的单链表，head 为表头，空表 head=-1。返回 [新表头, 反转后 nexts[0], nexts[1], ...]。最多 10000 个节点。注意输出是连接关系，不是节点值倒序。',
    [('nexts',V),('head',N)],V,[([[1,2,-1],0],[2,-1,0,1]),([[],-1],[-1]),([[-1],0],[0,-1]),([[2,-1,1],0],[1,-1,2,0])],
    '''
    def solve(nexts, head):
        links = nexts[:]
        prev, cur = -1, head
        while cur != -1:
            nxt = links[cur]
            links[cur] = prev
            prev, cur = cur, nxt
        return [prev] + links
    ''','''
    pub fn solve(mut nexts:Vec<i64>,head:i64)->Vec<i64>{
        let(mut prev,mut cur)=(-1,head);while cur!=-1{let i=cur as usize;let nxt=nexts[i];nexts[i]=prev;prev=cur;cur=nxt;}
        let mut out=vec![prev];out.extend(nexts);out
    }
    ''','维护已反转前缀的表头 prev 和未处理节点 cur。先保存原后继，再修改当前连接，再推进两个指针。',
    '时间 O(n)，本实现输出与复制空间 O(n)；连接修改本身 O(1) 辅助空间。','在覆盖 next 前必须保存后继，否则会丢失未处理部分。')

add('链表中是否有环', '链表', '进阶',
    'nexts[i] 为后继下标或 -1，head 为起点。判断从 head 可达的链表是否有环。保证下标合法，空表 head=-1；最多 10000 个节点。不可达节点的环不影响结果。',
    [('nexts',V),('head',N)],B,[([[1,2,1],0],True),([[1,-1],0],False),([[],-1],False),([[0],0],True),([[-1,1],0],False)],
    '''
    def solve(nexts, head):
        slow = fast = head
        while fast != -1 and nexts[fast] != -1:
            slow = nexts[slow]
            fast = nexts[nexts[fast]]
            if slow == fast: return True
        return False
    ''','''
    pub fn solve(nexts:Vec<i64>,head:i64)->bool{
        let(mut slow,mut fast)=(head,head);while fast!=-1&&nexts[fast as usize]!=-1{
        slow=nexts[slow as usize];fast=nexts[nexts[fast as usize]as usize];if slow==fast{return true;}}false
    }
    ''','慢指针每次一步，快指针每次两步。有环时它们在环上的相对位置每次改变一步，最终相遇；无环快指针到末尾。',
    '时间 O(n)，空间 O(1)。','不能在第一次移动前判断相等；快指针每次两次访问都需要边界保证。')

add('链表的中间节点', '链表', '基础',
    'nexts 表示无环链表，返回从 head 出发的中间节点下标。偶数长度取后一个中间节点，空表返回 -1；最多 10000 个节点。',
    [('nexts',V),('head',N)],N,[([[1,2,-1],0],1),([[1,2,3,-1],0],2),([[],-1],-1),([[-1],0],0)],
    '''
    def solve(nexts, head):
        slow = fast = head
        while fast != -1 and nexts[fast] != -1:
            slow = nexts[slow]
            fast = nexts[nexts[fast]]
        return slow
    ''','''
    pub fn solve(nexts:Vec<i64>,head:i64)->i64{
        let(mut slow,mut fast)=(head,head);while fast!=-1&&nexts[fast as usize]!=-1{
        slow=nexts[slow as usize];fast=nexts[nexts[fast as usize]as usize];}slow
    }
    ''','快指针走两步、慢指针走一步。快指针结束时慢指针位于后一个中间节点。',
    '时间 O(n)，空间 O(1)。','这里返回节点下标；下标值本身不代表它在链表中的位置。')

# 树采用堆式槽位：孩子为 2*i+1,2*i+2；-1 为不存在的节点。
add('二叉树最大深度', '树', '基础',
    'tree 用堆式槽位表示二叉树：下标 i 的孩子是 2i+1 和 2i+2，-1 表示空槽，节点值均非负。不允许非空节点位于空祖先下。返回最大深度，空树深度 0。槽位数不超过 2047。',
    [('tree',V)],N,[([[]],0),([[1]],1),([[1,2,3,-1,4]],3),([[-1]],0)],
    '''
    def solve(tree):
        def depth(i):
            if i >= len(tree) or tree[i] == -1: return 0
            return 1+max(depth(2*i+1), depth(2*i+2))
        return depth(0)
    ''','''
    pub fn solve(tree:Vec<i64>)->i64{
        fn depth(t:&[i64],i:usize)->i64{if i>=t.len()||t[i]==-1{0}else{1+depth(t,2*i+1).max(depth(t,2*i+2))}}
        depth(&tree,0)
    }
    ''','空子树深度为 0，非空树的深度为 1 加左右子树最大深度。函数语义在每个递归层保持一致。',
    '时间 O(可达节点数)，递归栈 O(h)。','堆式槽位不是紧凑的队列序列化；不要按数组长度推断树深度。')

add('二叉树中序遍历', '树', '基础',
    '使用堆式槽位 tree（孩子 2i+1、2i+2，-1 空槽，非负节点值），返回左子树→根→右子树的节点值序列。最多 2047 个槽位，空祖先下无非空节点。',
    [('tree',V)],V,[([[2,1,3]],[1,2,3]),([[]],[]),([[1,-1,2,-1,-1,3]],[1,3,2]),([[0]],[0])],
    '''
    def solve(tree):
        out = []
        def visit(i):
            if i >= len(tree) or tree[i] == -1: return
            visit(2*i+1); out.append(tree[i]); visit(2*i+2)
        visit(0)
        return out
    ''','''
    pub fn solve(tree:Vec<i64>)->Vec<i64>{
        fn visit(t:&[i64],i:usize,out:&mut Vec<i64>){if i>=t.len()||t[i]==-1{return;}
        visit(t,2*i+1,out);out.push(t[i]);visit(t,2*i+2,out);}
        let mut out=Vec::new();visit(&tree,0,&mut out);out
    }
    ''','按左、根、右递归访问。对二叉搜索树，中序结果递增；对普通树不能假设值有序。',
    '时间 O(n)，除输出外空间 O(h)。','参考实现借用 &[i64]，避免每层复制整棵树。')

add('二叉树逐层展开', '树', '基础',
    'tree 为堆式槽位树（-1 空槽、非负值、孩子 2i+1 和 2i+2）。返回二维数组，每行是一层，从左到右。不保留空槽。最多 2047 个槽位，空祖先下无非空节点。',
    [('tree',V)],'Vec<Vec<i64>>',[([[1,2,3,-1,4]],[[1],[2,3],[4]]),([[]],[]),([[7]],[[7]]),([[-1]],[])],
    '''
    def solve(tree):
        from collections import deque
        if not tree or tree[0] == -1: return []
        q, out = deque([0]), []
        while q:
            row = []
            for _ in range(len(q)):
                i = q.popleft(); row.append(tree[i])
                for j in (2*i+1, 2*i+2):
                    if j < len(tree) and tree[j] != -1: q.append(j)
            out.append(row)
        return out
    ''','''
    pub fn solve(tree:Vec<i64>)->Vec<Vec<i64>>{
        if tree.is_empty()||tree[0]==-1{return vec![];}let mut q=std::collections::VecDeque::from([0usize]);let mut out=Vec::new();
        while !q.is_empty(){let n=q.len();let mut row=Vec::new();for _ in 0..n{let i=q.pop_front().unwrap();row.push(tree[i]);
        for j in [2*i+1,2*i+2]{if j<tree.len()&&tree[j]!=-1{q.push_back(j);}}}out.push(row);}out
    }
    ''','队列执行广度优先搜索。每轮开始固定队列长度，只处理这一层，新增孩子留到下一轮。',
    '时间 O(n)，队列空间 O(树的最大宽度)。','一层的长度必须在入队新节点之前确定。')

add('根到叶的目标路径', '树', '进阶',
    'tree 为堆式槽位树（-1 空槽、非负值、孩子 2i+1 和 2i+2），判断是否存在根到叶的路径，其值之和等于 target。空树返回 false。最多 2047 槽位；target 非负。',
    [('tree',V),('target',N)],B,[([[5,4,8,11,-1,13,4],20],True),([[1,2,3],1],False),([[],0],False),([[0],0],True)],
    '''
    def solve(tree, target):
        def visit(i, remaining):
            if i >= len(tree) or tree[i] == -1: return False
            remaining -= tree[i]
            children = [j for j in (2*i+1, 2*i+2) if j < len(tree) and tree[j] != -1]
            if not children: return remaining == 0
            return any(visit(j, remaining) for j in children)
        return visit(0, target)
    ''','''
    pub fn solve(tree:Vec<i64>,target:i64)->bool{
        fn visit(t:&[i64],i:usize,r:i64)->bool{if i>=t.len()||t[i]==-1{return false;}
        let r=r-t[i];let(l,h)=(2*i+1,2*i+2);let left=l<t.len()&&t[l]!=-1;let right=h<t.len()&&t[h]!=-1;
        if !left&&!right{return r==0;}visit(t,l,r)||visit(t,h,r)}visit(&tree,0,target)
    }
    ''','沿路径扣减剩余目标，只在叶子处判断是否归零。非叶子即使当前和满足目标也不能提前接受。',
    '时间 O(n)，栈空间 O(h)。','根到叶必须结束在叶子，不能停在内部节点；空树不能算作和为零的路径。')

add('第 k 大的元素', '堆', '进阶',
    '返回 nums 排序后第 k 大的值，重复值分别计数。1≤k≤len(nums)≤10000，元素绝对值不超过 10⁶。',
    [('nums',V),('k',N)],N,[([[3,2,1,5,6,4],2],5),([[2,2,1],2],2),([[-3,-1],1],-1),([[5],1],5)],
    '''
    def solve(nums, k):
        import heapq
        heap = []
        for x in nums:
            heapq.heappush(heap, x)
            if len(heap) > k: heapq.heappop(heap)
        return heap[0]
    ''','''
    pub fn solve(nums:Vec<i64>,k:i64)->i64{
        use std::cmp::Reverse;let mut h=std::collections::BinaryHeap::new();
        for x in nums{h.push(Reverse(x));if h.len()>k as usize{h.pop();}}h.peek().unwrap().0
    }
    ''','维护大小最多 k 的小顶堆，留下已扫描元素中最大的 k 个。堆顶是这 k 个中最小值，也就是第 k 大。',
    '时间 O(n log k)，空间 O(k)。','Rust BinaryHeap 默认大顶堆，要用 Reverse；题目不是第 k 个不同的值。')

add('最小的 k 个数', '堆', '基础',
    '返回 nums 中最小的 k 个数，保留重复，输出按非递减排列。0≤k≤len(nums)≤10000。',
    [('nums',V),('k',N)],V,[([[3,1,2],2],[1,2]),([[2,2,1],2],[1,2]),([[],0],[]),([[4],0],[])],
    '''
    def solve(nums, k):
        import heapq
        heap = []
        for x in nums:
            heapq.heappush(heap, -x)
            if len(heap) > k: heapq.heappop(heap)
        return sorted(-x for x in heap)
    ''','''
    pub fn solve(nums:Vec<i64>,k:i64)->Vec<i64>{
        let mut h=std::collections::BinaryHeap::new();for x in nums{h.push(x);if h.len()>k as usize{h.pop();}}
        let mut out=h.into_vec();out.sort_unstable();out
    }
    ''','用大顶堆保留最小的 k 个元素，多出时弹出最大值。最后排序得到约定的输出顺序。',
    '时间 O(n log(k+1)+k log k)，空间 O(k)。','堆的内部数组并不整体有序；k=0 需要自然返回空结果。')

add('合并绳子的最小成本', '堆', '进阶',
    '每次合并两根绳子，成本为两者长度之和，新绳子可以继续合并。返回全部合并为一根的最小总成本。空输入或一根成本为 0；最多 10000 根，长度为 1～10⁶。',
    [('lengths',V)],N,[([[4,3,2,6]],29),([[1,2,3]],9),([[]],0),([[8]],0),([[1,1,1,1]],8)],
    '''
    def solve(lengths):
        import heapq
        heap = lengths[:]; heapq.heapify(heap)
        cost = 0
        while len(heap) > 1:
            s = heapq.heappop(heap)+heapq.heappop(heap)
            cost += s; heapq.heappush(heap, s)
        return cost
    ''','''
    pub fn solve(lengths:Vec<i64>)->i64{
        use std::cmp::Reverse;let mut h:std::collections::BinaryHeap<_>=lengths.into_iter().map(Reverse).collect();let mut cost=0;
        while h.len()>1{let s=h.pop().unwrap().0+h.pop().unwrap().0;cost+=s;h.push(Reverse(s));}cost
    }
    ''','每次合并最短两根。把合并看成二叉树，长绳应少参与重复计费；交换论证可将最短两个叶子放在最深的一对位置。',
    '时间 O(n log n)，空间 O(n)。','一次排序后相邻合并不够，新绳子必须重新参与最小值选择。')

add('网格中的陆地区域', '图与搜索', '进阶',
    'grid 为矩形 0/1 网格，1 为陆地，0 为水。上下左右连接的陆地算同一区域，返回区域数。空网格返回 0，行列均不超过 50。',
    [('grid','Vec<Vec<i64>>')],N,[([[[1,1,0],[0,1,0],[1,0,1]]],3),([[]],0),([[[0,0]]],0),([[[1,1],[1,1]]],1)],
    '''
    def solve(grid):
        if not grid: return 0
        rows, cols = len(grid), len(grid[0])
        seen, count = set(), 0
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] != 1 or (r,c) in seen: continue
                count += 1; stack = [(r,c)]; seen.add((r,c))
                while stack:
                    x,y = stack.pop()
                    for a,b in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                        if 0<=a<rows and 0<=b<cols and grid[a][b]==1 and (a,b) not in seen:
                            seen.add((a,b)); stack.append((a,b))
        return count
    ''','''
    pub fn solve(mut grid:Vec<Vec<i64>>)->i64{
        if grid.is_empty(){return 0;}let(r,c)=(grid.len(),grid[0].len());let mut count=0;
        for x in 0..r{for y in 0..c{if grid[x][y]!=1{continue;}count+=1;grid[x][y]=0;let mut s=vec![(x,y)];
        while let Some((a,b))=s.pop(){for(da,db)in [(1,0),(-1,0),(0,1),(0,-1)]{let(i,j)=(a as i64+da,b as i64+db);
        if i>=0&&j>=0&&(i as usize)<r&&(j as usize)<c&&grid[i as usize][j as usize]==1{
        grid[i as usize][j as usize]=0;s.push((i as usize,j as usize));}}}}}count
    }
    ''','扫描未访问陆地，每发现一次启动搜索并标记整个连通分量。用显式栈避免 Python 在大区域上的递归深度问题。',
    '时间 O(RC)，最坏空间 O(RC)。','入栈时就标记，避免同一格重复入栈；对角线不连接。')

add('无权图最短距离', '图与搜索', '进阶',
    '有 n 个节点 0～n-1，edges 每项 [u,v] 表示无向边。返回 source 到 target 的最少边数，无路返回 -1。1≤n≤200，端点合法，允许重复边和自环。',
    [('n',N),('edges','Vec<Vec<i64>>'),('source',N),('target',N)],N,[([4,[[0,1],[1,2],[0,3]],0,2],2),([3,[],0,2],-1),([1,[],0,0],0),([3,[[0,1],[1,1],[1,2]],0,2],2)],
    '''
    def solve(n, edges, source, target):
        from collections import deque
        graph = [[] for _ in range(n)]
        for u,v in edges: graph[u].append(v); graph[v].append(u)
        dist = [-1]*n; dist[source]=0; q=deque([source])
        while q:
            u=q.popleft()
            if u==target: return dist[u]
            for v in graph[u]:
                if dist[v]==-1: dist[v]=dist[u]+1; q.append(v)
        return -1
    ''','''
    pub fn solve(n:i64,edges:Vec<Vec<i64>>,source:i64,target:i64)->i64{
        let mut g=vec![vec![];n as usize];for e in edges{let(u,v)=(e[0]as usize,e[1]as usize);g[u].push(v);g[v].push(u);}
        let mut d=vec![-1;n as usize];d[source as usize]=0;let mut q=std::collections::VecDeque::from([source as usize]);
        while let Some(u)=q.pop_front(){if u==target as usize{return d[u];}for &v in &g[u]{if d[v]==-1{d[v]=d[u]+1;q.push_back(v);}}}-1
    }
    ''','无权图每条边代价相同。BFS 按距离从小到大扩展，节点首次发现时距离已经最短。',
    '时间 O(V+E)，空间 O(V+E)。','在入队时标记距离；有权图不能一般性地使用普通 BFS。')

add('图中的连通分量', '图与搜索', '基础',
    'n 个节点，edges 为无向边 [u,v]，返回连通分量数，包括孤立节点。0≤n≤200，所有边端点合法。',
    [('n',N),('edges','Vec<Vec<i64>>')],N,[([5,[[0,1],[1,2],[3,4]]],2),([3,[]],3),([0,[]],0),([2,[[0,1],[0,1]]],1)],
    '''
    def solve(n, edges):
        g=[[] for _ in range(n)]
        for u,v in edges: g[u].append(v); g[v].append(u)
        seen=set(); answer=0
        for start in range(n):
            if start in seen: continue
            answer+=1; seen.add(start); stack=[start]
            while stack:
                for v in g[stack.pop()]:
                    if v not in seen: seen.add(v); stack.append(v)
        return answer
    ''','''
    pub fn solve(n:i64,edges:Vec<Vec<i64>>)->i64{
        let n=n as usize;let mut g=vec![vec![];n];for e in edges{let(u,v)=(e[0]as usize,e[1]as usize);g[u].push(v);g[v].push(u);}
        let mut seen=vec![false;n];let mut ans=0;for start in 0..n{if seen[start]{continue;}ans+=1;seen[start]=true;let mut s=vec![start];
        while let Some(u)=s.pop(){for &v in &g[u]{if !seen[v]{seen[v]=true;s.push(v);}}}}ans
    }
    ''','每次从一个未访问节点开始搜索，就覆盖一个完整连通分量。遍历所有节点可把孤立点也计入。',
    '时间 O(V+E)，空间 O(V+E)。','不能只遍历边里出现的节点，否则会漏掉孤立点。')

add('课程能否全部完成', '图与搜索', '进阶',
    'n 门课编号 0～n-1。prerequisites 每项 [course, before] 表示 before 必须先于 course。判断是否存在完成全部课程的顺序。0≤n≤200，端点合法，无重复关系，可以有自依赖。',
    [('n',N),('prerequisites','Vec<Vec<i64>>')],B,[([2,[[1,0]]],True),([2,[[1,0],[0,1]]],False),([0,[]],True),([1,[[0,0]]],False)],
    '''
    def solve(n, prerequisites):
        from collections import deque
        g=[[] for _ in range(n)]; degree=[0]*n
        for course,before in prerequisites: g[before].append(course); degree[course]+=1
        q=deque(i for i in range(n) if degree[i]==0); done=0
        while q:
            u=q.popleft(); done+=1
            for v in g[u]:
                degree[v]-=1
                if degree[v]==0: q.append(v)
        return done==n
    ''','''
    pub fn solve(n:i64,prerequisites:Vec<Vec<i64>>)->bool{
        let n=n as usize;let mut g=vec![vec![];n];let mut deg=vec![0;n];
        for p in prerequisites{let(c,b)=(p[0]as usize,p[1]as usize);g[b].push(c);deg[c]+=1;}
        let mut q:std::collections::VecDeque<_>=(0..n).filter(|&i|deg[i]==0).collect();let mut done=0;
        while let Some(u)=q.pop_front(){done+=1;for &v in &g[u]{deg[v]-=1;if deg[v]==0{q.push_back(v);}}}done==n
    }
    ''','依赖关系构成有向图。反复移除入度零节点并减少后继入度；能移除所有节点当且仅当图无有向环。',
    '时间 O(V+E)，空间 O(V+E)。','注意 [course,before] 的边方向是 before→course；不是判断无向环。')

add('列出所有子集', '回溯', '进阶',
    'nums 包含互不相同的整数，长度不超过 10。返回所有子集，每个子集保持输入顺序。子集之间的顺序任意，空子集也必须包含。',
    [('nums',V)],'Vec<Vec<i64>>',[([[1,2]],[[],[1],[2],[1,2]]),([[]],[[]]),([[3]],[[],[3]]),([[0,-1]],[[],[0],[-1],[0,-1]])],
    '''
    def solve(nums):
        out=[[]]
        for x in nums:
            out += [s+[x] for s in out]
        return out
    ''','''
    pub fn solve(nums:Vec<i64>)->Vec<Vec<i64>>{
        let mut out=vec![vec![]];for x in nums{let n=out.len();for i in 0..n{let mut s=out[i].clone();s.push(x);out.push(s);}}out
    }
    ''','每个元素都有选与不选两种分支。迭代实现把已有子集复制一份并加入当前元素，恰好生成全部选择。',
    '时间与输出空间 O(n·2ⁿ)。','判题忽略外层顺序，内层顺序仍需符合输入；新增子集不能在同轮再次扩展。',unordered=True)

add('列出所有排列', '回溯', '进阶',
    'nums 元素互不相同，长度不超过 7。返回所有排列，外层顺序任意。空数组有一个空排列。',
    [('nums',V)],'Vec<Vec<i64>>',[([[1,2]],[[1,2],[2,1]]),([[]],[[]]),([[4]],[[4]]),([[0,-1]],[[0,-1],[-1,0]])],
    '''
    def solve(nums):
        out=[]; path=[]; used=[False]*len(nums)
        def dfs():
            if len(path)==len(nums): out.append(path[:]); return
            for i,x in enumerate(nums):
                if used[i]: continue
                used[i]=True; path.append(x); dfs(); path.pop(); used[i]=False
        dfs(); return out
    ''','''
    pub fn solve(nums:Vec<i64>)->Vec<Vec<i64>>{
        fn dfs(a:&[i64],used:&mut[bool],p:&mut Vec<i64>,out:&mut Vec<Vec<i64>>){if p.len()==a.len(){out.push(p.clone());return;}
        for i in 0..a.len(){if used[i]{continue;}used[i]=true;p.push(a[i]);dfs(a,used,p,out);p.pop();used[i]=false;}}
        let mut out=Vec::new();dfs(&nums,&mut vec![false;nums.len()],&mut Vec::new(),&mut out);out
    }
    ''','每一层确定一个位置，从未使用的元素中选择。递归返回时撤销路径和 used 标记，使下一分支状态恢复。',
    '时间与输出空间 O(n·n!)，递归辅助空间 O(n)。','保存路径时需要复制；回溯必须撤销全部被修改的状态。',unordered=True)

add('生成合法括号', '回溯', '进阶',
    '给定 0≤n≤7，生成所有由 n 对圆括号组成的合法字符串。结果顺序任意。n=0 返回包含空串的数组。',
    [('n',N)],'Vec<String>',[([0],['']),([1],['()']),([2],['(())','()()']),([3],['((()))','(()())','(())()','()(())','()()()'])],
    '''
    def solve(n):
        out=[]
        def dfs(s, left, right):
            if len(s)==2*n: out.append(s); return
            if left<n: dfs(s+'(',left+1,right)
            if right<left: dfs(s+')',left,right+1)
        dfs('',0,0); return out
    ''','''
    pub fn solve(n:i64)->Vec<String>{
        fn dfs(n:i64,l:i64,r:i64,s:String,out:&mut Vec<String>){if l+r==2*n{out.push(s);return;}
        if l<n{dfs(n,l+1,r,format!("{}(",s),out);}if r<l{dfs(n,l,r+1,format!("{})",s),out);}}
        let mut out=Vec::new();dfs(n,0,0,String::new(),&mut out);out
    }
    ''','前缀合法要求右括号数不超过左括号数。仅生成合法前缀，左括号不超过 n，右括号不超过已有左括号。',
    '时间与输出空间 O(n·Cₙ)，Cₙ 为第 n 个 Catalan 数。','先生成所有 2^(2n) 字符串再筛选浪费大量分支；n=0 有一个空解。',unordered=True)

add('不重复使用的组合和', '回溯', '进阶',
    'nums 是互不相同的正整数，长度不超过 15；每个元素最多使用一次。返回和为 target 的所有组合，每个组合内部升序，外层顺序任意。target 非负；target=0 包含空组合。',
    [('nums',V),('target',N)],'Vec<Vec<i64>>',[([[2,3,5,7],7],[[2,5],[7]]),([[1,2,3],3],[[1,2],[3]]),([[],0],[[]]),([[2,4],3],[])],
    '''
    def solve(nums, target):
        nums=sorted(nums); out=[]; path=[]
        def dfs(start, remaining):
            if remaining==0: out.append(path[:]); return
            for i in range(start,len(nums)):
                if nums[i]>remaining: break
                path.append(nums[i]); dfs(i+1,remaining-nums[i]); path.pop()
        dfs(0,target); return out
    ''','''
    pub fn solve(mut nums:Vec<i64>,target:i64)->Vec<Vec<i64>>{
        fn dfs(a:&[i64],start:usize,r:i64,p:&mut Vec<i64>,out:&mut Vec<Vec<i64>>){if r==0{out.push(p.clone());return;}
        for i in start..a.len(){if a[i]>r{break;}p.push(a[i]);dfs(a,i+1,r-a[i],p,out);p.pop();}}
        nums.sort_unstable();let mut out=Vec::new();dfs(&nums,0,target,&mut Vec::new(),&mut out);out
    }
    ''','排序后递归选择更靠后的元素，避免排列重复，也确保每个元素只用一次。正数条件允许在元素超过剩余目标时剪枝。',
    '最坏时间与输出空间 O(n·2ⁿ)。','递归下一起点是 i+1；用 i 会变成允许重复使用的另一道题。',unordered=True)

add('买卖一次的最大收益', '贪心', '基础',
    'prices 表示每天价格，只允许先买后卖一次，也可以不交易。返回最大利润。长度不超过 10000，价格非负且不超过 10⁶。',
    [('prices',V)],N,[([[7,1,5,3,6,4]],5),([[7,6,4,3]],0),([[]],0),([[2]],0)],
    '''
    def solve(prices):
        low=float('inf'); best=0
        for p in prices:
            best=max(best,p-low); low=min(low,p)
        return best
    ''','''
    pub fn solve(prices:Vec<i64>)->i64{
        let mut low=i64::MAX;let mut best=0;for p in prices{low=low.min(p);best=best.max(p-low);}best
    }
    ''','把每一天视为卖出日，最佳买入日是此前最低价。维护最低价与最大利润即可。',
    '时间 O(n)，空间 O(1)。','不能把最高价减最低价直接当答案，最低价可能出现在最高价之后。')

add('能否跳到末尾', '贪心', '进阶',
    'nums[i] 是在位置 i 最多向前跳几步。判断能否从下标 0 到最后一个位置。数组非空，长度不超过 10000，值为 0～10000。',
    [('nums',V)],B,[([[2,3,1,1,4]],True),([[3,2,1,0,4]],False),([[0]],True),([[0,1]],False)],
    '''
    def solve(nums):
        far=0
        for i,x in enumerate(nums):
            if i>far: return False
            far=max(far,i+x)
        return True
    ''','''
    pub fn solve(nums:Vec<i64>)->bool{
        let mut far=0usize;for(i,x)in nums.iter().enumerate(){if i>far{return false;}far=far.max(i+*x as usize);}true
    }
    ''','维护从已扫描可达位置能覆盖的最远下标。若当前位置越过最远边界，后续再大的跳跃值也无法使用。',
    '时间 O(n)，空间 O(1)。','不要求每次跳满；关注可达区间而不是某条具体跳跃路径。')

add('最多安排多少场会议', '贪心', '进阶',
    'intervals 每项 [start,end] 满足 start<end。选择最多数量的互不重叠会议，结束时刻等于另一场开始时刻可兼容。返回数量；最多 10000 场，时刻绝对值不超过 10⁶。',
    [('intervals','Vec<Vec<i64>>')],N,[([[[1,3],[2,4],[3,5],[0,6]]],2),([[]],0),([[[1,2],[2,3],[3,4]]],3),([[[-3,-1],[-2,0]]],1)],
    '''
    def solve(intervals):
        end=float('-inf'); count=0
        for s,e in sorted(intervals,key=lambda x:x[1]):
            if s>=end: count+=1; end=e
        return count
    ''','''
    pub fn solve(mut intervals:Vec<Vec<i64>>)->i64{
        intervals.sort_unstable_by_key(|x|x[1]);let mut end=i64::MIN;let mut count=0;
        for x in intervals{if x[0]>=end{count+=1;end=x[1];}}count
    }
    ''','优先选择结束最早的可兼容会议，为后续留出最大空间。任何最优方案的第一场都可替换为结束更早的一场而不减少数量。',
    '时间 O(n log n)，排序空间依语言实现而定。','按开始时间或持续时间贪心都可能错误；本题允许端点接触。')

add('合并覆盖区间', '贪心', '进阶',
    'intervals 每项 [start,end] 满足 start≤end。合并重叠或端点接触的闭区间，返回按起点升序排列的区间。最多 10000 项，端点绝对值不超过 10⁶。',
    [('intervals','Vec<Vec<i64>>')],'Vec<Vec<i64>>',[([[[1,3],[2,6],[8,10],[15,18]]],[[1,6],[8,10],[15,18]]),([[[1,4],[4,5]]],[[1,5]]),([[]],[]),([[[2,2],[1,3]]],[[1,3]])],
    '''
    def solve(intervals):
        out=[]
        for s,e in sorted(intervals):
            if out and s<=out[-1][1]: out[-1][1]=max(out[-1][1],e)
            else: out.append([s,e])
        return out
    ''','''
    pub fn solve(mut intervals:Vec<Vec<i64>>)->Vec<Vec<i64>>{
        intervals.sort_unstable();let mut out:Vec<Vec<i64>>=Vec::new();
        for x in intervals{if let Some(last)=out.last_mut(){if x[0]<=last[1]{last[1]=last[1].max(x[1]);continue;}}out.push(x);}out
    }
    ''','按起点排序后，新区间只能与最后一个合并结果重叠。重叠时扩展右边界，否则新增区间。',
    '时间 O(n log n)，输出空间 O(n)。','嵌套区间不能直接覆盖旧右端点，需要取最大值。')

add('分发饼干', '贪心', '基础',
    'needs 为孩子最低需求，cookies 为每块饼干大小，一人最多一块、一块最多给一人。返回最多满足的孩子数。两数组长度不超过 10000，数值均为 1～10⁶。',
    [('needs',V),('cookies',V)],N,[([[1,2,3],[1,1]],1),([[1,2],[1,2,3]],2),([[],[1]],0),([[2],[]],0)],
    '''
    def solve(needs, cookies):
        needs=sorted(needs); cookies=sorted(cookies); i=0
        for size in cookies:
            if i<len(needs) and size>=needs[i]: i+=1
        return i
    ''','''
    pub fn solve(mut needs:Vec<i64>,mut cookies:Vec<i64>)->i64{
        needs.sort_unstable();cookies.sort_unstable();let mut i=0;
        for x in cookies{if i<needs.len()&&x>=needs[i]{i+=1;}}i as i64
    }
    ''','从最小需求和最小饼干开始，用最小的可满足饼干满足当前孩子。更小的饼干无法满足他，也无法满足后续孩子。',
    '时间 O(n log n+m log m)，除排序外空间 O(1)。','不要把大饼干优先给需求小的孩子，可能浪费满足高需求的机会。')

# 动态规划从状态语义开始。
add('一步或两步上台阶', '动态规划', '基础',
    '到达 n 级台阶，每次走 1 或 2 级，返回不同走法数。0≤n≤50；n=0 定义为一种空走法。',
    [('n',N)],N,[([0],1),([1],1),([2],2),([5],8),([50],20365011074)],
    '''
    def solve(n):
        a=b=1
        for _ in range(n): a,b=b,a+b
        return a
    ''','''
    pub fn solve(n:i64)->i64{let(mut a,mut b)=(1i64,1i64);for _ in 0..n{let c=a+b;a=b;b=c;}a}
    ''','dp[i] 是到第 i 级的走法数。最后一步来自 i-1 或 i-2，两类互斥，因此相加。dp[0]=dp[1]=1，只依赖前两项可滚动保存。',
    '时间 O(n)，空间 O(1)。','dp[0]=1 是组合计数的空方案，不是无路可走；i64 才能容纳 n=50 的答案。')

add('不选相邻房屋', '动态规划', '基础',
    'nums 为每间房的非负收益，不能选择相邻两间。返回最大收益，可以一间不选。长度不超过 10000，值不超过 10⁶。',
    [('nums',V)],N,[([[1,2,3,1]],4),([[2,7,9,3,1]],12),([[]],0),([[0,0]],0)],
    '''
    def solve(nums):
        prev2=prev1=0
        for x in nums: prev2,prev1=prev1,max(prev1,prev2+x)
        return prev1
    ''','''
    pub fn solve(nums:Vec<i64>)->i64{let(mut a,mut b)=(0,0);for x in nums{let c=b.max(a+x);a=b;b=c;}b}
    ''','dp[i] 为前 i 间房最优收益。不选第 i 间是 dp[i-1]，选择则为 dp[i-2]+收益，取最大。初始空前缀收益为零。',
    '时间 O(n)，空间 O(1)。','更新滚动状态前先计算新值，避免误用本轮更新后的状态。')

add('最大连续子数组和', '动态规划', '基础',
    'nums 非空，返回非空连续子数组的最大和。长度不超过 10000，元素绝对值不超过 10⁶。',
    [('nums',V)],N,[([[-2,1,-3,4,-1,2,1,-5,4]],6),([[-3,-2,-5]],-2),([[1]],1),([[0,-1,0]],0)],
    '''
    def solve(nums):
        ending=best=nums[0]
        for x in nums[1:]:
            ending=max(x,ending+x); best=max(best,ending)
        return best
    ''','''
    pub fn solve(nums:Vec<i64>)->i64{let mut ending=nums[0];let mut best=ending;for &x in &nums[1..]{ending=x.max(ending+x);best=best.max(ending);}best}
    ''','dp[i] 是恰好以 i 结尾的最大非空子数组和，只能新开一段或接上上一段。全局答案是所有结尾状态的最大值。',
    '时间 O(n)，空间 O(1)。','状态必须以当前位置结尾；全负数组不能允许空子数组或初始化答案为零。')

add('凑金额的最少硬币', '动态规划', '进阶',
    'coins 为互不相同的正整数面值，每种无限使用。返回凑出 amount 的最少硬币数，无解 -1。0≤amount≤2000，最多 20 种，面值不超过 2000。',
    [('coins',V),('amount',N)],N,[([[1,2,5],11],3),([[2],3],-1),([[],0],0),([[2,5],10],2)],
    '''
    def solve(coins, amount):
        dp=[amount+1]*(amount+1); dp[0]=0
        for x in range(1,amount+1):
            for c in coins:
                if c<=x: dp[x]=min(dp[x],dp[x-c]+1)
        return -1 if dp[amount]>amount else dp[amount]
    ''','''
    pub fn solve(coins:Vec<i64>,amount:i64)->i64{
        let a=amount as usize;let mut dp=vec![amount+1;a+1];dp[0]=0;
        for x in 1..=a{for &c in &coins{if c as usize<=x{dp[x]=dp[x].min(dp[x-c as usize]+1);}}}
        if dp[a]>amount{-1}else{dp[a]}
    }
    ''','dp[x] 是金额 x 的最少枚数。枚举最后一枚硬币 c，候选为 dp[x-c]+1。dp[0]=0，不可达状态设大于任何合法枚数的哨兵。',
    '时间 O(amount·种类数)，空间 O(amount)。','最大面值优先不总是最优，例如 [1,3,4] 凑 6；这是最小值问题，不是组合计数。')

add('硬币组合有多少种', '动态规划', '进阶',
    'coins 为互不相同的正整数，每种无限使用。返回凑出 amount 的组合数，顺序不同不算新组合。0≤amount≤100，种类≤10，保证答案可用 i64 表示。',
    [('coins',V),('amount',N)],N,[([[1,2,5],5],4),([[2],3],0),([[],0],1),([[2,3],7],1)],
    '''
    def solve(coins, amount):
        dp=[0]*(amount+1); dp[0]=1
        for c in coins:
            for x in range(c,amount+1): dp[x]+=dp[x-c]
        return dp[amount]
    ''','''
    pub fn solve(coins:Vec<i64>,amount:i64)->i64{
        let a=amount as usize;let mut dp=vec![0i64;a+1];dp[0]=1;
        for c in coins{for x in c as usize..=a{dp[x]+=dp[x-c as usize];}}dp[a]
    }
    ''','状态含义是使用已处理面值凑出金额 x 的组合数。外层枚举硬币，内层金额正序，允许当前硬币重复使用但不会计入顺序排列。',
    '时间 O(amount·种类数)，空间 O(amount)。','金额外层会把不同顺序计成排列；dp[0]=1 表示空组合。')

add('每件物品最多一次的背包', '动态规划', '进阶',
    'weights、values 等长，表示每件物品正整数重量和非负价值。每件最多一次，返回总重量不超过 capacity 的最大价值。物品≤100，capacity≤2000，价值≤10⁶。',
    [('weights',V),('values',V),('capacity',N)],N,[([[1,3,4],[15,20,30],4],35),([[],[],3],0),([[2],[5],1],0),([[1],[2],3],2)],
    '''
    def solve(weights, values, capacity):
        dp=[0]*(capacity+1)
        for w,v in zip(weights,values):
            for c in range(capacity,w-1,-1): dp[c]=max(dp[c],dp[c-w]+v)
        return dp[capacity]
    ''','''
    pub fn solve(weights:Vec<i64>,values:Vec<i64>,capacity:i64)->i64{
        let c=capacity as usize;let mut dp=vec![0;c+1];for(w,v)in weights.into_iter().zip(values){
        for x in (w as usize..=c).rev(){dp[x]=dp[x].max(dp[x-w as usize]+v);}}dp[c]
    }
    ''','dp[c] 是已处理物品在容量 c 内的最大价值。处理新物品时容量倒序，确保 dp[c-w] 仍来自上一轮，从而不重复取当前物品。',
    '时间 O(n·capacity)，空间 O(capacity)。','正序会变成完全背包；容量不必恰好装满，初始收益可设零。')

add('分成等和的两组', '动态规划', '进阶',
    'nums 为正整数数组，判断能否把所有元素分成和相等的两组。空数组视为可分。长度≤100，总和≤4000。',
    [('nums',V)],B,[([[1,5,11,5]],True),([[1,2,3,5]],False),([[]],True),([[2]],False),([[1,1]],True)],
    '''
    def solve(nums):
        total=sum(nums)
        if total%2: return False
        target=total//2; dp=[False]*(target+1); dp[0]=True
        for x in nums:
            for s in range(target,x-1,-1): dp[s]=dp[s] or dp[s-x]
        return dp[target]
    ''','''
    pub fn solve(nums:Vec<i64>)->bool{
        let total:i64=nums.iter().sum();if total%2!=0{return false;}let t=(total/2)as usize;
        let mut dp=vec![false;t+1];dp[0]=true;for x in nums{for s in (x as usize..=t).rev(){dp[s]=dp[s]||dp[s-x as usize];}}dp[t]
    }
    ''','总和奇数必无解。偶数时转成能否选出总和一半的 0/1 子集和问题；布尔状态记录金额是否可达。',
    '时间 O(n·总和)，空间 O(总和)。','每个元素只允许一次，金额要倒序；总和一半可达就保证余下元素也是一半。')

add('最长严格递增子序列', '动态规划', '进阶',
    '返回 nums 的最长严格递增子序列长度，允许跳过元素但必须保持顺序。空输入返回 0，长度≤1000，值绝对值≤10⁶。',
    [('nums',V)],N,[([[10,9,2,5,3,7,101,18]],4),([[2,2,2]],1),([[]],0),([[-1,0,1]],3)],
    '''
    def solve(nums):
        dp=[1]*len(nums)
        for i in range(len(nums)):
            for j in range(i):
                if nums[j]<nums[i]: dp[i]=max(dp[i],dp[j]+1)
        return max(dp,default=0)
    ''','''
    pub fn solve(nums:Vec<i64>)->i64{
        let mut dp=vec![1;nums.len()];for i in 0..nums.len(){for j in 0..i{if nums[j]<nums[i]{dp[i]=dp[i].max(dp[j]+1);}}}
        dp.into_iter().max().unwrap_or(0)
    }
    ''','dp[i] 是以 i 结尾的最长严格递增子序列长度。从所有更小的前驱 j 转移，答案取各结尾最大值。可进一步用最小尾值表与二分优化。',
    '基础解时间 O(n²)，空间 O(n)；进阶解可到 O(n log n)。','严格递增使用 < 而不是 ≤；子序列与连续子数组不同。')

add('两段文本的公共子序列', '动态规划', '进阶',
    'a、b 为 ASCII 字符串，返回最长公共子序列长度。子序列可不连续，必须保留原顺序。每串长度≤300。',
    [('a',S),('b',S)],N,[(['abcde','ace'],3),(['abc','def'],0),(['','a'],0),(['aaa','aa'],2)],
    '''
    def solve(a, b):
        dp=[0]*(len(b)+1)
        for x in a:
            prev=0
            for j,y in enumerate(b,1):
                old=dp[j]
                dp[j]=prev+1 if x==y else max(dp[j],dp[j-1])
                prev=old
        return dp[-1]
    ''','''
    pub fn solve(a:String,b:String)->i64{
        let b=b.as_bytes();let mut dp=vec![0;b.len()+1];for x in a.bytes(){let mut prev=0;
        for j in 1..=b.len(){let old=dp[j];dp[j]=if x==b[j-1]{prev+1}else{dp[j].max(dp[j-1])};prev=old;}}dp[b.len()]
    }
    ''','dp[i][j] 是两串前 i、j 个字符的 LCS。末尾相同则取左上角加一，不同则取删去任一末尾的最大值。滚动数组要保存上一行左上角。',
    '时间 O(nm)，空间 O(m)。','更新前的 dp[j] 是上方，更新后的 dp[j-1] 是左方；prev 保存旧左上角。')

add('把文本变成另一段的代价', '动态规划', '进阶',
    'a、b 为 ASCII 字符串，插入、删除、替换一个字符各花费 1。返回 a 变成 b 的最小编辑次数。每串长度≤300。',
    [('a',S),('b',S)],N,[(['horse','ros'],3),(['','abc'],3),(['same','same'],0),(['ab','ba'],2)],
    '''
    def solve(a, b):
        dp=list(range(len(b)+1))
        for i,x in enumerate(a,1):
            prev=dp[0]; dp[0]=i
            for j,y in enumerate(b,1):
                old=dp[j]
                dp[j]=prev if x==y else 1+min(prev,dp[j],dp[j-1])
                prev=old
        return dp[-1]
    ''','''
    pub fn solve(a:String,b:String)->i64{
        let b=b.as_bytes();let mut dp:Vec<i64>=(0..=b.len()).map(|x|x as i64).collect();
        for(i,x)in a.bytes().enumerate(){let mut prev=dp[0];dp[0]=i as i64+1;for j in 1..=b.len(){let old=dp[j];
        dp[j]=if x==b[j-1]{prev}else{1+prev.min(dp[j]).min(dp[j-1])};prev=old;}}dp[b.len()]
    }
    ''','dp[i][j] 为前缀变换最小代价。字符相同直接沿对角线；不同则在删除、插入、替换三个来源中取最小再加一。空前缀边界分别为 i 与 j。',
    '时间 O(nm)，空间 O(m)。','边界不是零；一次交换字符不属于允许操作。')

add('网格中的不同路线', '动态规划', '基础',
    'rows×cols 网格，从左上角到右下角，每次只向右或向下。返回路线数。1≤rows,cols≤20，答案在 i64 范围。',
    [('rows',N),('cols',N)],N,[([3,7],28),([1,1],1),([1,5],1),([2,2],2)],
    '''
    def solve(rows, cols):
        dp=[1]*cols
        for _ in range(1,rows):
            for j in range(1,cols): dp[j]+=dp[j-1]
        return dp[-1]
    ''','''
    pub fn solve(rows:i64,cols:i64)->i64{
        let mut dp=vec![1i64;cols as usize];for _ in 1..rows{for j in 1..cols as usize{dp[j]+=dp[j-1];}}dp[cols as usize-1]
    }
    ''','每格只能从上方或左方到达，路径数相加。第一行与第一列只有一种路线；滚动数组保存上方状态，左侧已更新为当前行。',
    '时间 O(rows·cols)，空间 O(cols)。','路线计数不取最小值；初始边界为一，与障碍网格不同。')

add('网格中的最小路径总和', '动态规划', '进阶',
    'grid 为非空矩形非负整数网格，左上到右下只向右或下，返回沿路格子值的最小总和，包括起终点。行列≤100，单格≤10⁶。',
    [('grid','Vec<Vec<i64>>')],N,[([[[1,3,1],[1,5,1],[4,2,1]]],7),([[[5]]],5),([[[1,2,3]]],6),([[[0,0],[0,0]]],0)],
    '''
    def solve(grid):
        dp=[float('inf')]*len(grid[0]); dp[0]=0
        for row in grid:
            for j,x in enumerate(row): dp[j]=min(dp[j],dp[j-1] if j else float('inf'))+x
        return dp[-1]
    ''','''
    pub fn solve(grid:Vec<Vec<i64>>)->i64{
        let m=grid[0].len();let mut dp=vec![i64::MAX/4;m];dp[0]=0;
        for row in grid{for j in 0..m{let left=if j>0{dp[j-1]}else{i64::MAX/4};dp[j]=dp[j].min(left)+row[j];}}dp[m-1]
    }
    ''','dp[r][c] 为到该格的最小和，来源是上方与左方的较小值，再加当前格。不可达边界用足够大的哨兵，起点之前累计值为零。',
    '时间 O(RC)，空间 O(C)。','别忘记起点值；Rust 的无穷哨兵留出加法余量以免溢出。')

add('文本能否按词切分', '动态规划', '进阶',
    'text 与 words 均只含小写英文，words 中词非空，可重复使用。判断 text 能否完整切成词典中的词。空串为 true，text 长度≤300，词典≤100 项。',
    [('text',S),('words','Vec<String>')],B,[(['leetcode',['leet','code']],True),(['catsandog',['cats','dog','sand','and','cat']],False),(['',[]],True),(['aaaa',['aa']],True)],
    '''
    def solve(text, words):
        words=set(words); dp=[False]*(len(text)+1); dp[0]=True
        for i in range(1,len(text)+1):
            dp[i]=any(dp[j] and text[j:i] in words for j in range(i))
        return dp[-1]
    ''','''
    pub fn solve(text:String,words:Vec<String>)->bool{
        let s:std::collections::HashSet<String>=words.into_iter().collect();let mut dp=vec![false;text.len()+1];dp[0]=true;
        for i in 1..=text.len(){for j in 0..i{if dp[j]&&s.contains(&text[j..i]){dp[i]=true;break;}}}dp[text.len()]
    }
    ''','dp[i] 表示长度 i 的前缀能否切分。枚举最后一个词的起点 j，只要前缀 j 可切且 [j,i) 是词就可达。',
    '检查 O(n²) 个切分点；考虑切片与哈希字符成本最坏 O(n³)，空间 O(n+词典总长度)。','Rust 字符串切片按字节，本题小写 ASCII 才可用任意下标；贪心取最长词可能阻断后续切分。')

add('最长回文子序列', '动态规划', '进阶',
    'text 为 ASCII 字符串，返回最长回文子序列长度，可以跳过字符。空串为 0，长度≤300。',
    [('text',S)],N,[(['bbbab'],4),(['cbbd'],2),([''],0),(['a'],1),(['abc'],1)],
    '''
    def solve(text):
        n=len(text)
        if not n: return 0
        dp=[[0]*n for _ in range(n)]
        for i in range(n-1,-1,-1):
            dp[i][i]=1
            for j in range(i+1,n):
                dp[i][j]=dp[i+1][j-1]+2 if text[i]==text[j] else max(dp[i+1][j],dp[i][j-1])
        return dp[0][n-1]
    ''','''
    pub fn solve(text:String)->i64{
        let s=text.as_bytes();let n=s.len();if n==0{return 0;}let mut dp=vec![vec![0;n];n];
        for i in (0..n).rev(){dp[i][i]=1;for j in i+1..n{dp[i][j]=if s[i]==s[j]{dp[i+1][j-1]+2}else{dp[i+1][j].max(dp[i][j-1])};}}dp[0][n-1]
    }
    ''','区间状态 dp[i][j] 是闭区间的最长回文子序列。两端相同可包住内部回文，否则去掉任一端取最大。左端倒序、右端正序确保依赖已算。',
    '时间 O(n²)，空间 O(n²)。','相邻两端相同时内部为空，长度为零；子序列不是最长连续回文子串。')

add('解码数字文本', '动态规划', '进阶',
    'text 是非空数字串，1～26 分别映射 A～Z，返回解码方式数。0 不能单独解码，允许出现前导零但那可能导致无解。长度≤40，答案在 i64 范围。',
    [('text',S)],N,[(['12'],2),(['226'],3),(['06'],0),(['10'],1),(['100'],0)],
    '''
    def solve(text):
        dp=[0]*(len(text)+1); dp[0]=1
        for i in range(1,len(text)+1):
            if text[i-1]!='0': dp[i]+=dp[i-1]
            if i>=2 and 10<=int(text[i-2:i])<=26: dp[i]+=dp[i-2]
        return dp[-1]
    ''','''
    pub fn solve(text:String)->i64{
        let s=text.as_bytes();let mut dp=vec![0i64;s.len()+1];dp[0]=1;
        for i in 1..=s.len(){if s[i-1]!=b'0'{dp[i]+=dp[i-1];}if i>=2{let x=(s[i-2]-b'0')*10+s[i-1]-b'0';
        if (10..=26).contains(&x){dp[i]+=dp[i-2];}}}dp[s.len()]
    }
    ''','按最后一个编码长度分类：末位非零可单独编码，末两位在 10～26 可整体编码。两类互斥，前缀方式数相加。',
    '时间 O(n)，空间 O(n)，可进一步滚动为 O(1)。','06 不能按 6 解读；0 只能参与 10 或 20。')

add('最少平方数分解', '动态规划', '进阶',
    '给定 0≤n≤2000，返回和为 n 的正整数平方数最少数量。同一个平方数可重复使用，n=0 为 0。',
    [('n',N)],N,[([0],0),([12],3),([13],2),([1],1),([16],1)],
    '''
    def solve(n):
        dp=[0]+[n+1]*n
        for x in range(1,n+1):
            j=1
            while j*j<=x:
                dp[x]=min(dp[x],dp[x-j*j]+1); j+=1
        return dp[n]
    ''','''
    pub fn solve(n:i64)->i64{
        let n=n as usize;let mut dp=vec![n as i64+1;n+1];dp[0]=0;
        for x in 1..=n{let mut j=1;while j*j<=x{dp[x]=dp[x].min(dp[x-j*j]+1);j+=1;}}dp[n]
    }
    ''','这是面值为平方数的最少硬币问题。dp[x] 枚举最后选的平方数 j²，取 dp[x-j²]+1 的最小值。',
    '时间 O(n√n)，空间 O(n)。','平方数必须为正；枚举 0 会产生没有进展的转移。')

assert len(PROBLEMS) == 63, len(PROBLEMS)
BY_ID = {p['id']:p for p in PROBLEMS}

# Supplemental expected values come from independent small-input oracles.
from pathlib import Path
import json
_extra = Path(__file__).with_name('extra_cases.json')
if _extra.exists():
    for _pid, _cases in json.loads(_extra.read_text(encoding='utf-8')).items():
        BY_ID[_pid]['cases'].extend(_cases)
