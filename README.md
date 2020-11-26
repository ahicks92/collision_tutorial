# A Collision Tutorial

This is a collision tutorial demonstrating some basic collision optimizations, with the primary goal of being approachable to new blind programmers.  Put another way, there's no graphics here.
I got tired of having this conversation over and over, so figured I'd finally just get sample code with explanations going on.  The rest of this README explains what's going on here and all the optimizations performed.

If you're trying to use Python and you need axis-aligned bounding box collision, you can drop this tutorial  into your project and use it as-is.  It has full test coverage and is reasonably efficient.

people are always like "What's better than the two nested for loops".  What's better than the two nested for loops is this, and a number of more advanced optimizations not described here.

there are benchmarks at the bottom of this file proving that the code here is fast enough for most practical use scases. Note that if you try to feed a tilemap to it without some preprocessing, it's going to be unhappy.
You can either process collisions with a tilemap yourself, or see the notes at the bottom of the file as to how you might go about extending this for that use case.

You'll want to clone this repository and follow along in the code.  I don't paste most of it here because this README is already going to be long enough.
There's actually not that much code, just enough that trying to put little 5 line examples inline isn't going to cut it.

I don't intend to maintain this, but am happy enough if someone else wants to turn it into a real package. In practice, though, properly building a quadtree functions much better than what is presented here.  This code would make a good stepping stone to being able to understand quadtrees, as this is something like half the implementation of one.

Code was developed against Python 3.7 on Windows.  If you want to run the tests, create a virtualenv and do:

```
pip install -r requirements.txt
pytest
```

# Preliminaries, Motivation, and Defining terms

## Defining the Problem

You've got:

- Some number of axis-aligned bounding boxes, hereafter AABB. This means boxes that can't rotate.  The sides are always either north-south or east-west.
- They're spread out pretty evenly, and all generally around the same size.
- You want it to be fast.

This doesn't work on anything but AABB.  Spheres, no.  Rotating boxes, no.  More complex polygons, no.  The basic idea does generalize, but the code here doesn't get into it for simplicity.

## What's Wrong with nested for loops?

most people wanting to do AABB collisions start with something like this:

```
for a in boxes:
    for b in boxes:
        check(a, b)
```

Check will be something like "for all corners of box a, see if they're in box b".  I'm not going to write pseudocode for that here because it's lengthy and wrong, as we will see below.

The above is something called `O(n^2)`, which means in the worst case it takes `n^2` checks to figure out if the list of boxes has collisions.  Additionally, the above is `Omega(n^2)`, which means that it *always*
takes `n^2` operations.  Put another way, 5 boxes is 25 checks, 100 boxes is 10000 checks, and 1000 boxes is 1000000 checks.
We can do significantly better.

This tutorial will talk heavily about how many operations things take in the worst case, because that's important here. Much of this code looks at first glance as though it should be slower, but one of the primary lessons this tutorial should teach is that
code complexity doesn't at all equate to performance.  What I am about to present is an order of magnitude faster than the above algorithm.

## What's Wrong with the Basic Box Check

As stated above, many developers start by checking if all the corners of box a are inside box b and vice versa.  But consider two boxes overlapping to form a cross, for example:

```
a = Box(x = -100, y = 0, width  = 200, height = 1)
b = Box(x = 0, y = -100, width = 1, height = 200)
```

These boxes intersect at the origin, but don't have any corners inside thew other box.

Additionally, the naive check is *16* comparisons without optimization.  There's nothing like slow *and* incorrect to really cause a problem.

## Some Basic Python Performance Tips

Before we get started, it's worth noting the following.  I don't have sources handy for these; they just come from my experience.  I don't even promise they're all correct:

- Local variables are the fastest kind of variable.
- Attribute lookups are faster than attribute lookups and computing with the attribute.
- Allocation is heavily optimized. You can make lists and throw them out all day long, and Python will mostly be fine with this.  There are other problems with lists, but continually asking the OS for memory isn't one of them.
- Python won't inline or anything like that unless it's Cython.  Cython won't inline a lot.  Pypy will be very good at inlining, but running Pypy everywhere isn't practical.

Anyway, with this out of the way, let's get started.

# Defining Your Box

Every box in this code (`collision_tutorial.box.Box`) has the following:

- `x` and `y`, the bottom left corner.
- `x2` and `y2`, the upper right corner.
- `cx` and `cy`, the center of the box.
- `width` and `height`, the width and height.
- `half_width`, `half_height`: half the width and height (see below).
- `stationary`, whether or not we expect the box to move around.
- `manager`, an internal property that lets boxes link to a `BoxManager`, which we'll discuss near the bottom of this document,.

Each of `x`, `cx`, `x2`, etc. are used as part of a different optimization, below. We cache the values on the object to prevent the cost of  recomputing. `half_width` and `half_height` are two very useful values for the collision check.
`stationary` and `manager` are used in the stationary box optimization, which can be used to make levels with mostly stationary objects function much faster.

To use this code correctly, always go through the public methods. Don't manipulate the properties.  If you read the `box` module, you can see that there's some basic math going on to recompute them when it moves.  Just doing `box.x = 12` will not work.  Also, you can't change a box from stationary to not stationary after creation.  We'll talk about stationary later.

For completeness, the box constructor is:

```
class Box:
    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        userdata: Any = None,
        stationary: bool = False,
    ) -> None:
```

Userdata can be used to associate the box with something in your app.

# A Better Collision Check

This is a bit hard to explain without a graphic, but the correct collision check for boxes is:

```
abs(a.cx - b.cx) <= (a.half_width + b.half_width)
and abs(a.cy - b.cy) <= (a-half_height + b.half_height)
```

It is easy to see how this works by considering what happens on the x axis when two boxes overlap left to right. Continue the vertical sides downward, and you'll get two line segments on the X axis,
like a shadow.  These line segments won't overlap if the boxes collide, because that means they're far apart enough in the x direction to not be touching.
You can easily tell if two line segments on the X axis intersect by just finding out if their centers are close enough.

But that's not enough.  It's possible that two boxes with the same X don't collide in Y, so we do the same check on the Y axis. If they're close enough together that both the X axis and Y axis show them
as colliding, they have to be colliding--there's no third dimension they can be apart on.

You might have to work at visualizing this.  If there's any part of this tutorial that you might want to take my word for, it's probably this section.

# Optimization 0: A Digression Into Generators

Assume that you have 100 objects and they're all colliding for some reason.  This is going to generate 10000 (or 5000, we'll get to that) pairs.  Naively, you might do:

```
list.append((a, b))
return list
```

But this will build lists of 10000 items that you immediately throw away.  Fortunately, we can do better.  This function is a generator:

```
def gen():
    yield 1
    yield 2
    yield 3
```


And the following:

```
for i in gen():
    print(i)
```

Will print the numbers 1 to 3.  At no point does this build an in-memory list.  In fact, if you just do:

```
gen()
```

Nothing much happens.  Generators stop at the yield statements and wait for you to ask for more values.  If you don't, they just stop.  In addition,
they never build stuff up in memory: if `gen()` wanted to yield 10000 items, it'd use the same amount of memory as it did for 3.

If you want to know more, look up a tutorial on generators.  The two most important facts for using this code are these:

- The only thing you can do with a generator is `for i in gen()` or other operations that access the next item. You can't index them, etc.
- You can get from a generator to a list (or set, or whatever else) by just doing `list(gen())`.

Most of the code here uses generators to avoid large lists.

# Optimization 1: Get Good  Base Algorithms

no matter what we do, we'll eventually have to check a list of boxes and there won't be any choice but to use the inefficient algorithm.  Most of the trick here is making those lists smaller.
But since we have no choice, we'll need the inefficient algorithms in here somewhere so that we can handle that.
Additionally, we probably want tests.  To get that, we can test against the boring algorithm that we know is right.  I'll say more on testing later.

In `collision_tutorial.base_algorithms`, you will find two functions:

- `check_exhaustive` is the naive check where you do 2 nested for loops.
- `check_deduplicated` is a better version that cuts the comparisons in half.

Let's first consider `check_exhaustive`:

```
def check_exhaustive(boxes: List[Box]) -> Iterable[Tuple[Box, Box]]:
    for a in boxes:
        for b in boxes:
            # If the centers of the boxes are close enough together that they overlap in the x and y axis both, they overlap.
            # See the readme for the edge cases with box detection: in particular, it's not sufficient to check if one of the corners
            # is inside the other box.
            if (
                a is not b
                and abs(a.cx - b.cx) <= (a.half_width + b.half_width)
                and abs(a.cy - b.cy) <= (a.half_height + b.half_height)
            ):
                yield (a, b)
```

This is the boring algorithm with the 2 nested loops.  If boxes 1 and 2 collide, you get `(1, 2)` and `(2, 1)`.  It's also the worst algorithm you'll see here:
for x items, it takes `x^2` checks.  But it's even worse than that: we also have to check to make sure that we're not going to return `(2, 2)` for example--we're also checking boxes against themselves.

It might seem like there's no point to this function.  But we can point at it and easily say "Yes, this one works".  If the output of the others doesn't match it, something is broken.
Unfortunately, "match" is one of those funny words with more complexity: as I keep saying, testing is near the end of this document, and I'll cover it there.

Next, we have:

```
def check_deduplicated(boxes: List[Box]) -> Iterable[Tuple[Box, Box]]:
    # Save the len function call.
    l = len(boxes)
    for i in range(l):
        # The inner loop only does l to the end of the boxes.
        for j in range(i + 1, l):
            a = boxes[i]
            b = boxes[j]
            if abs(a.cx - b.cx) <= (a.half_width + b.half_width) and abs(
                a.cy - b.cy
            ) <= (a.half_height + b.half_height):
                yield (a, b)
```

Which cuts the comparisons in half. It is worth considering why this works.  Suppose we have boxes `a`, `b`, and `c`.  The loop will first check `a` against `b` and `c`.
When the outer loop gets to `b`, we've already checked `b` against `a` (because we checked `a` against `b` last time). So we avoid doing that.
And when the outer loop gets to `c`, we've checked `c` against `b` and `a` already, when we did `a` and `b` against `c` previously.
The same pattern holds for bigger examples.

Additionally, we get to drop the check to make sure that we aren't going to return `(a, a)`.

Now our 100 objects case is only 5000 checks.  This is the version that we use moving forward: if we have to check a list of boxes and can't
use any other tricks, it's the best we've got to throw at the problem.

# So How Can We Do Better: An introduction To Partitioning

The big trick of this entire thing is to divide the list of boxes into smaller sublists.  Suppose that we have 100 objects, with our 5000 comparisons from the above optimized function, but we can somehow
divide our 100 objects into two lists of 50 each.  Then we have:

```
2 * (50 * 50 / 2) = 2500
```

Which is again half the comparisons.  But this gets even better--what if we can divide it into 4 lists of 25?  In that case:

```
4 * (25 * 25 / 2) = 2 * 25 * 25 = 1250
```

Which is a 4th of the original checks.  But how about an extreme case?  What if we can get it down to just `5`?  Well:

```
20 * (5 * 5 / 2) = 10 * 5 * 5 = 250
```

In the genral case, we can do exactly this.  To understand how, we'll use one of those really lame analogies that textbooks love to come up with in order to supposedly hold your interest, only in this case it's to make up for a diagram.

Suppose that you've got the standard archetypical medieval town with 4 gates and two really boring roads that meet in the middle, and it's under siege from the west and the east with two really big armies of boxes.  For the sake of argument, let's say they're 500 boxes each.  Our naive collision detection algorithm
would check the west army against everyone in the west army, then against everyone in the east army.  Then it'll check everyone in the east army against themselves, then against the west army.

But hang on, there's a big town in the middle.  There's no way the west army can collide with the east unless the town goes away first.  The town divides the world into two partitions: everything to the west of it, and everything to the east.  So instead of checking everything with everything else,
we can handle the partitions separately.  In doing so, we split the list.

In practice, what we actually want to do, though, is split based on a point.  To do this, consider that the two main streets of this town actually divide the world into 4 quadrants: the northwest, northeast, southwest, and southeast.
Anyone that's not standing on one of those streets has to be in one of those 4 partitions.  Everyone in the northwest partition only needs to be checked against the people in that partition.

But there is one really important edge case.  Anyone in the center is going to be in all 4 partitions.  And anyone standing on one of the roads is going to be in at least two of them.
To understand why, consider a really tall box standing on the west street.  It's going to have part of itself in the southwest and part of itself in the northwest.
So what we're about to do must account for this, and allow objects to be in more than one partition at once.

# Optimization 2: partition the world

This is where I stop pasting code because it's too much.  To see this in practice, read `collision_tutorial.partitioner`.

To partition the world well, we want to pick a center point of all the boxes, then divide the world into 4 quadrants.

To get the center, you can just do an average of all the `x` values for the `x` coordinate, then all the `y` values for the `y` coordinate.  This isn't perfect, but it's good enough to be going on with in most cases.

Then, build 4 lists, where some boxes can be in up to all of them, as described above.  After that, check the lists individually and combine the pairs, and you've got a useful subdivision.

it's worth taking a moment to point out that this can go wrong, however.  Imagine that for some reason every box is colliding with every other box. In that case, what actually happens is you get 4 partitions containing all the boxes, then check them all. One of the key insights for optimizing is to realize that in the general case you only care about the usual cases.
While the worst case might happen and it's bad if it does, any game which has every object clumped together colliding with every other object in such a fashion as to make partitioning useless probably has other problems.

# Optimization 3:  Partition Recursively

You've partitioned once, but all the partitions are still really big.  You can just re-run your partitioning algorithm over and over until they're small enough, or until you give up.

The way this tutorial does this is by fixing the number of iterations and the minimum partition size.  I didn't put a lot of thought into optimizing these numbers.
In particular, more than 2 or 3 repetitions is probably much better, and playing around with the maximum partition size is probably also a good way to get more or less performance.
But this is only a demo, so I didn't put in the time.

It's important to note that raising the number of iterations makes the worst case of everything overlapping and not being able to partition at all worse. Again, this shouldn't ever happen in practice without other problems, but if it does then iterating deeper into the tree
without dealing with this will magnify the problem.  There are a lot of ways to deal with this, for example you can detect that partitions didn't shrink because one of them is the same length
as the input, or you could say "any partition which doesn't divide equally doesn't get partitioned further".  Or any other number of heuristics.  But again, this is a tutorial, though admittedly one that can be used as-is, not a fully featured library.

# Stateful can be Better: an Introduction to `BoxManager`

So far, we've just had a big list of boxes that you get from somewhere and pass to this tutorial code.  But that's kind of inefficient, in the sense that we're rebuilding the partitions every time and we aren't really taking advantage of any information we have.
There's a lot that can be done if we take one step further and introduce something that can hold state.  For example, we might avoid repartitioning on every tick, cache some of the collisions, only run
things close to the player, and keep statistics on what's going on in order to change behavior at runtime.
Most of these aren't implemented here because this is a tutorial, at this point a refrain in these later parts of the document.

The way the manager works is as follows: you `.register()` your boxes and `.remove(box)` them to get rid of it.  This has the downside that your boxes won't be garbage collected
unless you remember to remove them.  But it lets the manager be aware of movement when it happens via `box.move`, which lets us implement:

# Optimization 4: The Stationary Box Optimization

let's say that your level has lots of power-ups and scenery, none of which moves often, for example platforms.  It's really a shame that we're checking them against everything including all the other stationary stuff.  Here's how to do better (see `box_manager.BoxManager`).

For the first run, and any run where something stationary has moved, execute the normal partitioning algorithm.  Then, for every item that run would return, add the pair to the stationary cache if `a.stationary and b.stationary`.
The stationary cache is a cache of all pairs of stationary objects which have collided with each other.  We invalidate it whenever a stationary object moves
because stationary objects shouldn't move often.

Next, if the stationary cache is valid, start by yielding everything in the stationary cache.  Then, modify the partitioning algorithm as follows.

We know that we want to check every nonstationary box against every stationary box as well as every nonstationary box against any other nonstationary box.  Consider the optimized base algorithm `check_deduplicated`.  if we have a list that looks like:

```
n, n, n, s, s
```

Where `n` is nonstationary and `s` is stationary, then by the time we get to the first stationary box, we've checked all the `n` against all the `s` as well as all the other `n`.
We can thus stop at the first stationary box and abort the algorithm early.

To get the list in this order you simply do a sort `partition.sort(key=lambda o: o.stationary)` since `true : false` in Python.  This puts all the stationary ones at the right end and lets the above
trick function.

This actually means that we can consider all stationary boxes free in the grand scheme of things.  This leads to the second-to-last tweak to this algorithm: we can raise the partition size so that the average number of nonstationary boxes
in the partition is of a specificed size.  For example, if 30% of boxes are stationary and we want a partition size of 10 disregarding this algorithm, we can use a partition size of
around 15.  See the code for specifically how this is done, but as an overview, if 30% of boxes are stationary, 70% aren't,
and 70% of 15 is 10.5.

The last optimization here is that we maintain a count of stationary boxes.  If there currently aren't any, we don't bother with any of this and fall back to the partitioner.
One good future direction for the bored and/or interested is to modify this so that you can specify a minimum number of stationary boxes before the optimization kicks in.  In particular, a very good way of doing this would be to specify a percent, and then to
tweak the code in a real project to find the number that optimizes the most.  The reason you'd not want to use an absolute value here is that there's a big difference between 10 out of 100 stationary boxes
and 10 out of 1000: in the latter case not optimizing at all might be better.

# So How Fast is it?

Obviously there's no point to any of this if it isn't fast.  Consequently I've prepared some benchmarks.  To duplicate these, either run `benchmark.py` or `benchmark_cython.py` against a Python interpreter of your choice.
I've run these on a machine with an Intel `I7-8700` at 3.20 GHZ.
They work by producing lists of random boxes (fixed using a seed, or put another way every run uses the same list), then running them through one of the above algorithms.  We report 3 values for each combination: the number of objects, the average time per iteration, and the estimate of how many times you can run it in a second.  Results follow:

## CPython 3.7:

Benchmarking exhaustive

objects | time/iteration | number per second
----- | ----- | -----
0 | 9.230000000000349e-06 | 108342.36186348453
100 | 0.0014479800000000002 | 690.6172737192502
200 | 0.00560564 | 178.391762581971
300 | 0.012880220000000001 | 77.63842543062152
400 | 0.023779629999999996 | 42.052798971220334
500 | 0.035957275 | 27.81078377046092
600 | 0.054175835000000006 | 18.458414161959848
700 | 0.070621715 | 14.159950661067917
800 | 0.09308099999999997 | 10.74333107723381
900 | 0.11951879500000002 | 8.366884890363895
1000 | 0.14509465000000005 | 6.892052877208083

Benchmarking deduplicated

objects | time/iteration | number per second
----- | ----- | -----
0 | 9.715000000021234e-06 | 102933.6078227292
100 | 0.0008335899999999619 | 1199.630513801804
200 | 0.0033079450000000677 | 302.3024868914022
300 | 0.007542199999999966 | 132.58730874280775
400 | 0.013775004999999929 | 72.59525495635066
500 | 0.02166019000000006 | 46.16764672886052
600 | 0.03151497499999998 | 31.730946954582723
700 | 0.04350998499999994 | 22.983230171189472
800 | 0.057080239999999983 | 17.519197536660677
900 | 0.07478089000000007 | 13.37240035522443
1000 | 0.09146961999999999 | 10.932591608011492

Benchmarking partitioned

objects | time/iteration | number per second
----- | ----- | -----
0 | 1.326999999999856e-05 | 75357.950263761
100 | 0.0001422749999999695 | 7028.641714990084
200 | 0.0003944650000001104 | 2535.0791578459944
300 | 0.0008490050000000693 | 1177.8493648446338
400 | 0.0014417249999999272 | 693.6135532088647
500 | 0.0020571550000001437 | 486.1082417221503
600 | 0.0029712799999998653 | 336.55528930294196
700 | 0.00376171499999991 | 265.8361943953819
800 | 0.004964475000000057 | 201.4311684518481
900 | 0.006271730000000098 | 159.44563940092837
1000 | 0.007463165000000061 | 133.99140981071594

Benchmarking manager, stationary probability of 0.1

objects | time/iteration | number per second
----- | ----- | -----
0 | 1.1761999999997386e-05 | 85019.55449755333
100 | 0.00015824099999999674 | 6319.474725260967
200 | 0.0004183280000000167 | 2390.4687231071316
300 | 0.0008947649999999996 | 1117.6118869200297
400 | 0.0014634570000000124 | 683.3135514060143
500 | 0.0021618819999999774 | 462.55993620373846
600 | 0.0030425200000000173 | 328.67491421584555
700 | 0.0038541129999999767 | 259.46307230743
800 | 0.005040613999999976 | 198.38852965134896
900 | 0.006513566999999974 | 153.52571025983215
1000 | 0.007667062999999991 | 130.42804004610386

Benchmarking manager, stationary probability 0.5

objects | time/iteration | number per second
----- | ----- | -----
0 | 9.511999999993747e-06 | 105130.36164851318
100 | 0.00013020600000000825 | 7680.137628065809
200 | 0.0003160649999999876 | 3163.9061585434615
300 | 0.0007253090000000029 | 1378.7227236943097
400 | 0.0011827139999999758 | 845.5129473397799
500 | 0.0016807730000000022 | 594.9643408122326
600 | 0.002458053000000007 | 406.8260529777011
700 | 0.0031407310000000164 | 318.3972138970179
800 | 0.004085332999999984 | 244.7780878572209
900 | 0.004965090999999973 | 201.40617765112572
1000 | 0.0061083219999999725 | 163.71108137390343

Benchmarking manager, stationary probability 0.9

objects | time/iteration | number per second
----- | ----- | -----
0 | 1.2840999999994551e-05 | 77875.55486336144
100 | 7.873599999999925e-05 | 12700.670595407557
200 | 0.0002289689999999922 | 4367.4034476284305
300 | 0.0005707089999999937 | 1752.20646599232
400 | 0.0005970499999999745 | 1674.901599531099
500 | 0.0008111219999999975 | 1232.8601616033138
600 | 0.0010551440000000057 | 947.7379390869821
700 | 0.0013082740000000114 | 764.3658744269101
800 | 0.0016301750000000225 | 613.4310733510121
900 | 0.002132263999999999 | 468.985078770734
1000 | 0.002292611999999998 | 436.18370661934983

## Python 3.7, using Cython's `pyximport`:

Benchmarking exhaustive

objects | time/iteration | number per second
----- | ----- | -----
0 | 1.3274999999990379e-05 | 75329.56685504518
100 | 0.0007397850000000039 | 1351.7440878092889
200 | 0.0030827599999999843 | 324.38464233349504
300 | 0.006709530000000008 | 149.04173615737596
400 | 0.012212230000000001 | 81.88512663125407
500 | 0.01931741499999997 | 51.76676071824318
600 | 0.027751294999999974 | 36.034354432829204
700 | 0.03781276999999998 | 26.44609215352381
800 | 0.049791145000000016 | 20.083892427057055
900 | 0.06384556 | 15.662796285285932
1000 | 0.08037423499999993 | 12.441798046351556

Benchmarking deduplicated

objects | time/iteration | number per second
----- | ----- | -----
0 | 9.905000000021146e-06 | 100959.11155960274
100 | 0.0004466349999999508 | 2238.9647027217084
200 | 0.0017581250000000103 | 568.7877710629188
300 | 0.004134990000000016 | 241.83855341850793
400 | 0.007526799999999945 | 132.85858532178446
500 | 0.011958670000000015 | 83.62133916229804
600 | 0.01811227000000004 | 55.21119108758857
700 | 0.024654759999999953 | 40.56011901961333
800 | 0.032300044999999944 | 30.959709189259698
900 | 0.04143498499999998 | 24.13419481146187
1000 | 0.05161202499999993 | 19.37532968334417

Benchmarking partitioned

objects | time/iteration | number per second
----- | ----- | -----
0 | 9.7850000000399e-06 | 102197.24067408506
100 | 8.562999999996989e-05 | 11678.150181015433
200 | 0.00022785499999997683 | 4388.756007110231
300 | 0.0005175649999999976 | 1932.1244674582026
400 | 0.0008622500000000421 | 1159.7564511452028
500 | 0.001243015000000014 | 804.4955209711779
600 | 0.0017815149999999668 | 561.3200001122744
700 | 0.002223234999999946 | 449.7950059260602
800 | 0.0029538050000000203 | 338.5463833936205
900 | 0.0036914900000000195 | 270.89332491757926
1000 | 0.004461195000000018 | 224.15518711914544

Benchmarking manager, stationary probability of 0.1

objects | time/iteration | number per second
----- | ----- | -----
0 | 9.353000000000834e-06 | 106917.56655617565
100 | 9.707999999999828e-05 | 10300.782859497505
200 | 0.00024975200000000087 | 4003.9719401646294
300 | 0.0005561900000000009 | 1797.9467448174157
400 | 0.0009100670000000122 | 1098.8201967547297
500 | 0.0013459169999999964 | 742.987866265158
600 | 0.0019186559999999986 | 521.1981720537714
700 | 0.002395215000000004 | 417.4990554083865
800 | 0.0030832639999999857 | 324.3316174028577
900 | 0.003758543000000003 | 266.06054526980245
1000 | 0.004506795999999991 | 221.8871233577029

Benchmarking manager, stationary probability 0.5

objects | time/iteration | number per second
----- | ----- | -----
0 | 9.721000000002533e-06 | 102870.075095128
100 | 8.009299999999442e-05 | 12485.485622964174
200 | 0.0001933430000000058 | 5172.155185344026
300 | 0.00046717299999999185 | 2140.5346627480985
400 | 0.0007585399999999965 | 1318.322039707866
500 | 0.0010443330000000017 | 957.5489810242503
600 | 0.0015038229999999864 | 664.9718750145523
700 | 0.001967157999999998 | 508.34757553790854
800 | 0.0024634839999999867 | 405.9291637372134
900 | 0.0030715640000000023 | 325.5670401137659
1000 | 0.003707680999999994 | 269.71036612912536

Benchmarking manager, stationary probability 0.9

objects | time/iteration | number per second
----- | ----- | -----
0 | 9.867999999997323e-06 | 101337.65707339595
100 | 4.6362000000002014e-05 | 21569.38872352264
200 | 0.0001318279999999916 | 7585.641897017808
300 | 0.00035880399999999924 | 2787.036933813453
400 | 0.0004086799999999968 | 2446.9022217872366
500 | 0.000555228999999997 | 1801.0586622816988
600 | 0.000746380000000002 | 1339.8001018248042
700 | 0.0009029269999999912 | 1107.509244933433
800 | 0.0011542209999999998 | 866.3852069924219
900 | 0.0014966019999999958 | 668.1803178132883
1000 | 0.0016205809999999942 | 617.0626460510173


## Pypy3.7:

Benchmarking exhaustive

objects | time/iteration | number per second
----- | ----- | -----
0 | 1.5499999999999998e-06 | 645161.2903225807
100 | 0.00026720499999999996 | 3742.4449392788315
200 | 0.00023393500000000006 | 4274.691687862012
300 | 0.0005238 | 1909.1256204658264
400 | 0.0007029999999999998 | 1422.4751066856334
500 | 0.00111719 | 895.1028920774444
600 | 0.0015581500000000006 | 641.7867342682024
700 | 0.002094955 | 477.3372220405689
800 | 0.0026505649999999993 | 377.2780520379618
900 | 0.00345516 | 289.42219752486136
1000 | 0.0042033750000000005 | 237.90406518571382

Benchmarking deduplicated

objects | time/iteration | number per second
----- | ----- | -----
0 | 2.6250000000005436e-06 | 380952.3809523021
100 | 0.0002515599999999979 | 3975.194784544476
200 | 0.00014030999999999904 | 7127.075760815386
300 | 0.00034418999999999975 | 2905.3720328888135
400 | 0.000597735000000002 | 1672.9821743749264
500 | 0.00069129 | 1446.5709036728435
600 | 0.0009737350000000005 | 1026.9734578709808
700 | 0.0013067949999999995 | 765.2309658362639
800 | 0.0017704700000000019 | 564.8217704903212
900 | 0.0026494650000000036 | 377.43468964489006
1000 | 0.0026495250000000024 | 377.4261424217545

Benchmarking partitioned

objects | time/iteration | number per second
----- | ----- | -----
0 | 1.7700000000009374e-06 | 564971.7514121302
100 | 0.0006927599999999978 | 1443.50135689128
200 | 0.0002728499999999967 | 3665.0174088327367
300 | 0.0006761300000000025 | 1479.0055166905718
400 | 0.001389275000000001 | 719.7998956290146
500 | 0.0006088599999999999 | 1642.4136911605297
600 | 0.0003543650000000009 | 2821.9491202573545
700 | 0.0010669499999999999 | 937.2510426917851
800 | 0.0004573299999999947 | 2186.604858636021
900 | 0.0005697950000000008 | 1755.0171552926906
1000 | 0.000500624999999999 | 1997.5031210986306

Benchmarking manager, stationary probability of 0.1

objects | time/iteration | number per second
----- | ----- | -----
0 | 1.8980000000001773e-06 | 526870.3898840393
100 | 0.0004328080000000001 | 2310.493336537217
200 | 0.0003857350000000004 | 2592.453368245036
300 | 0.000630016000000001 | 1587.2612759041015
400 | 0.00034040700000000036 | 2937.6599188618297
500 | 0.0003599770000000002 | 2777.955258252609
600 | 0.00047627399999999984 | 2099.6317245955065
700 | 0.0005002019999999996 | 1999.1923263001763
800 | 0.0006608860000000005 | 1513.1202658249672
900 | 0.0007052329999999985 | 1417.971081897759
1000 | 0.0008280869999999996 | 1207.6025828204047

Benchmarking manager, stationary probability 0.5

objects | time/iteration | number per second
----- | ----- | -----
0 | 4.627000000001491e-06 | 216122.75772631896
100 | 0.00030355700000000096 | 3294.274221974775
200 | 0.0002589279999999983 | 3862.0774887227594
300 | 0.00030192100000000057 | 3312.124694870506
400 | 0.00021982900000000027 | 4548.990351591458
500 | 0.00037080400000000013 | 2696.842536757963
600 | 0.00041008399999999947 | 2438.5247900430186
700 | 0.000402610000000001 | 2483.793249049943
800 | 0.0004770540000000012 | 2096.1987531809764
900 | 0.0006977089999999997 | 1433.2622912990953
1000 | 0.0005837969999999992 | 1712.9241842626827

Benchmarking manager, stationary probability 0.9

objects | time/iteration | number per second
----- | ----- | -----
0 | 4.5849999999991734e-06 | 218102.50817888338
100 | 0.0001258009999999987 | 7949.0624080890475
200 | 0.0001323019999999997 | 7558.464724645148
300 | 0.00012952100000000134 | 7720.755707568577
400 | 0.00023696799999999962 | 4219.9790689038255
500 | 0.0002718149999999997 | 3678.972830785649
600 | 0.00023967599999999978 | 4172.299270682091
700 | 0.00028168199999999865 | 3550.102597965098
800 | 0.0003523999999999994 | 2837.6844494892216
900 | 0.0005640990000000001 | 1772.7384732112623
1000 | 0.00040585300000000045 | 2463.9463056821037


# Testing: How Do We Know if it Works?

For something like this, I like to use a tool called [Hypothesis](https://hypothesis.readthedocs.io/en/latest/), which can intelligently generate tests with input data for you, and even go so far as to hunt for
and print example broken programs.  I'm not going to provide a full overview of it here, but if you look at the tests directory, it's pretty straightforward stuff.

The one complexity we have with the tests is that we need to deal with the fact that we might get `(a, b)` from one algorithm, then have the other report `(b, a)`.  There's a few ways of dealing with this, two of which are used here.
For the case of testing the `check_exhaustive` we duplicate the pairs returned by `check_deduplicated` and then check that test.  For the `BoxManager` tests, we flip the pairs so that `id(a)` <= ~id(b)`.  Either case
yields sets which are equal if the collisions are equal.

By linking this to the base algorithm `check_exhaustive`, we can verify that this works, even better than if a human tested it by hand.  The only point of failure is if `check_exhaustive` itself isn't working.
AAdmittedly, I should probably introduce more manual testing around that, but haven't for lack of time.  Though i'm not generally interested in maintaining this code, if you uncovera  bug and submit a PR with a fix and/or better tests,
i'll be happy to accept it.

# Future Directions

I've mentioned a few future directions above.  I'll go ahead and reiterate some of them here, as well as provide a few more, in case someone wants to turn this into a proper library.

- Cythonize the entire thing properly.  `pyximport` isn't redistributable and has horrible performance.  This code is already fast enough to be used in many practical projects, but cythonizing it properly by converting it to `pyx` with proper Cython typing and etc. can probably get an order of magnitude performance improvement out of it.
- Figure out how to deal with the worst cases of partitioning.
- Figure out better values for some of the parameters, in particular the maximum partitionsize and the number of iterations.
- Figure out better heuristics for stopping partitioning early, since iteration count is really kind of a hack.
- Optimize the partitioner to not create as many lists.
- Figure out better heuristics for when to apply and when not to apply the stationary object optimization.
- Some better manual tests for the base case probably won't uncover bugs, but they certainly can't hurt anything.


# Bonus: tilemaps

You have two choices with tilemaps.  The first, and easiest, is to simply handle it yourself.

The second is to combine impassable rectangles into boxes, for example a 2 by 2 square of dirt becomes a 2 by 2 box.  Then you pass those boxes to this code.  I'm not going to provide an algorithm for that: it's a bit hard to write and I don't have the time.  But essentially you find all impassable
tiles that aren't part of a box yet, and then you keep trying to extend the rectangle in the x and/or y direction as much as possible in a loop.  You'd want to cache the output: this is as slow as it sounds.

But at runtime, as the above benchmarks show, you're not going to get more than 1000 boxes or so.  It's practical, but not if you throw thousands of 1-tiel boxes at it.

You might be saying "but other languages can", but that's not exactly true: you'll be able to push it a bit further, but not far enough.  You'll also have ram issues, since boxes are actually 6 or 7 values.