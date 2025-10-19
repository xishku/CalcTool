
class Fibonacci:
    @staticmethod
    def fibonacci(n):
        if n <= 0:
            return []
        elif n == 1:
            return [0]
        elif n == 2:
            return [0, 1]
        else:
            fib_list = [0, 1]
            for _ in range(2, n):
                new_num = fib_list[-1] + fib_list[-2]
                fib_list.append(new_num)
            return fib_list
        
if __name__ == '__main__':
    print(Fibonacci.fibonacci(100))
