# Ivich Desktop Pet

这里是Desktop Pet Ivich , 依维希桌宠（个人oc）

## 安装

```bash
python -m pip install -e ".[dev]"
```

## 运行

```bash
desktop-pet
```

也可以直接以模块方式运行：

```bash
python -m desktop_pet
```

## 测试

```bash
python -m pytest -q
```

## 资源

动画资源会根据 `assets/config/animation.json` 中每个动画的 `pattern` 加载，例如
`assets/character/idle/idle_%02d.png`，也支持角色子目录或特效目录中的嵌套路径。

动画速度和是否循环同样在 `assets/config/animation.json` 中配置。
当 `frames` 为 `0` 时，程序会从 `01` 开始按序扫描文件，直到遇到第一个缺失帧为止。
