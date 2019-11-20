from multiprocessing import Pool


def func1(x):

    return 2*x


def example1():

    values1 = [i for i in range(0, 1000)]

    with Pool(processes=5) as pool:

        results = []

        for y in pool.imap(func1, values1):

            results.append(y)

        print(results)


class func2:

    def __init__(self, i, x):

        self._i = i
        self._x = x

    def __call__(self, *args, **kwargs):

        return self._i * self._x


class func3:

    def __init__(self, i, x):

        self._i = i
        self._x = x

    def __call__(self, *args, **kwargs):

        return self._i + self._x


def _func2(f):

    return f()


def func_generator():
    for i in range(0, 1000):

        yield func2(i, i) if i % 2 == 0 else func3(i, i)


def example2():

    # values2 = [func2(i, i) if i % 2 == 0 else func3(i, i) for i in range(0, 1000)]

    values2 = func_generator()

    with Pool(processes=5) as pool:

        results = []

        for y in pool.imap(_func2, values2):

            results.append(y)

        print(results)


def example():
    example2()
