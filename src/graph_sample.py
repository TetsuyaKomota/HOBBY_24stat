import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

plt.rcParams["font.family"] = "MS Gothic"

# N の i番目の点に働く力を計算
def calc(N, E):
    F = []
    for i in range(len(N)):
        f = np.zeros(2)
        for j, e in enumerate(E[i]):
            if e > 0:
                # 隣接する点とは，結合力の逆数の距離になるように力が働く
                v = N[j] - N[i]                 # ベクトル i->j
                d = np.linalg.norm(v) - (1/e)   # 目的地までの距離
                r = E[j][j]/(E[i][i] + E[j][j]) # 質量比
                f = f + v*d*r
        F.append(f)

    return [N[i] + F[i] for i in range(len(N))]

# 描画メソッド
def plot(data):
    global N
    plt.cla()
    N = calc(N, E)
    x = [n[0] for n in N]
    y = [n[1] for n in N]

    plt.scatter(x, y)
    for i in range(len(E)):
        plt.text(N[i][0], N[i][1], S[i])
        for j in range(i+1, len(E)):
            if E[i][j] > 0:
                plt.plot([N[i][0], N[j][0]], [N[i][1], N[j][1]])
    plt.xlim(min(x)-1, max(x)+1)
    plt.ylim(min(y)-1, max(y)+1)
    plt.axis("off")


# チャンネル名
S = [
        "月ノ美兎", 
        "樋口楓", 
        "静凛", 
        "える", 
        "モイラ", 
        "鈴谷アキ", 
        "勇気ちひろ", 
        "渋谷ハジメ", 
    ]

# 質量-結合力行列
# ii項が質量(登録者数)，ij項が結合力(コラボ回数)
"""
E = [
        [1, 2, 3, 0], 
        [2, 2, 1, 0], 
        [3, 1, 3, 2], 
        [0, 0, 2, 4], 
    ]

"""
E = np.random.randint(-10, 10, [len(S), len(S)])
E = np.tril(E) + np.tril(E, k=-1).T
E = E * (E > 0)
print(E)

if __name__ == "__main__":
    N = [np.random.random(2) for _ in range(len(E))]
    fig = plt.figure()
    ani = animation.FuncAnimation(fig, plot, interval=100)
    plt.show()
    
