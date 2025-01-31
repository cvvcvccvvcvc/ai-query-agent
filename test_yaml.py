from itertools import chain
urls1 = [1,2,3,4]
urls2 = [5,6,7,8]
print(list(chain(*zip(urls1, urls2))))
list(chain(*zip(urls1, urls2)))