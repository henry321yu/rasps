import matplotlib.pyplot as plt

# 生成 100 個顏色
colors = []
num=[3,5,7]
for j in range(100):
    r = ((j + num[0])% num[2]) / num[2]
    g = ((j + num[1]) % num[1]) / num[1]
    b = ((j + num[2]) % num[0]) / num[0]
    colors.append((r, g, b))

# 隨機數據生成
x = [0,1]

# 繪製每個顏色的線條
plt.figure(figsize=(10, 6))

for i, color in enumerate(colors[:30]):  # 只顯示前 10 個顏色
    plt.plot([0, 100], [i, i],label=f'Color {i+1}', color=colors[i], linewidth=2)

plt.title('Generated Colors with Minimum Difference')
plt.xlabel('X-axis')
plt.ylabel('Y-axis')
plt.legend(title='Colors')
plt.grid()
plt.tight_layout()
plt.show()

