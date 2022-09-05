# ZHKU-Connector

一个简单的仲恺农业工程学院校园网自动登录助手，还能在检测到失去互联网连接时自动登录。

## 启动之前的环境搭建
在启动之前，需要下载一些依赖包，运行如下命令

```shell
pip install requests
pip install pyquery
```

或者根据依赖清单安装，运行如下命令

```shell
pip install -r requirements.txt
```

## 如何启动

通过python命令启动，在所在文件夹内，运行如下命令

```shell
python Connector.py
```

如果环境里的有python3，也可以试试使用python3命令：

```shell
python3 Connector.py
```

也可以通过login文件运行：给login赋权后，就可以通过更简单的命令来运行了。
注意，如果环境是python3，那么需要将login里面的命令python改为python3

```shell
chmod 777 ./login # 赋权
./login # 启动
```

## 保持后台运行

Linux:

```shell

```

Windows:

```shell

```

## TODO

- [ ]  后台运行
- [X]  输入密码不可见
- [ ] 下线功能