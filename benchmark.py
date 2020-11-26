import timeit

from collision_tutorial import (
    test_helpers,
    box,
    base_algorithms,
    partitioner,
    box_manager,
)


def gen_boxes(n, stationary_probability=0.0):
    # Generate some boxes with a reasonable chance of overlapping.
    return test_helpers.generate_random_boxes(
        n=n,
        seed=n,
        min_x=0.0,
        max_x=1000.0,
        min_y=0.0,
        max_y=1000.0,
        min_width=1.0,
        max_width=20.0,
        min_height=1.0,
        max_height=20.0,
        stationary_probability=stationary_probability,
    )


def benchmark(algorithm):
    print("")
    print("objects | time/iteration | number per second")
    print("----- | ----- | -----")
    for i in range(0, 1001, 100):
        boxes = gen_boxes(i)
        time = timeit.timeit(lambda: list(algorithm(boxes)), number=20) / 20
        # We wrap it in a list because it's a generator, and we need to exhaust it.
        print(f"{i} | {time} | {1.0/time}")
    print("")


def benchmark_stationary_stage(n, stationary_probability):
    manager = box_manager.BoxManager()
    boxes = gen_boxes(n, stationary_probability=stationary_probability)
    for b in boxes:
        manager.register(b)
    # The first one builds the stationary cache.
    list(manager.yield_collisions())
    # Now we time the next one:
    time = timeit.timeit(lambda: list(manager.yield_collisions()), number=100) / 100
    print(f"{n} | {time} | {1.0 / time}")


def benchmark_stationary(stationary_probability):
    print("")
    print("objects | time/iteration | number per second")
    print("----- | ----- | -----")
    for n in range(0, 1001, 100):
        benchmark_stationary_stage(n, stationary_probability)
    print("")


def main():
    print("Benchmarking exhaustive")
    benchmark(base_algorithms.check_exhaustive)
    print("Benchmarking deduplicated")
    benchmark(base_algorithms.check_deduplicated)
    print("Benchmarking partitioned")
    benchmark(partitioner.check_partitioned)
    print("Benchmarking manager, stationary probability of 0.1")
    benchmark_stationary(0.1)
    print("Benchmarking manager, stationary probability 0.5")
    benchmark_stationary(0.5)
    print("Benchmarking manager, stationary probability 0.9")
    benchmark_stationary(0.9)


if __name__ == "__main__":
    main()
