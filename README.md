# ZHKU-Connector

一个简单的仲恺农业工程学院校园网自动登录助手，还能在检测到失去互联网连接时自动登录。

## ✨快速开始

下载打包好的应用程序直接运行即可

| 平台    | 下载                                                                                                                     |
|-------|------------------------------------------------------------------------------------------------------------------------|
| Windows | [win-1.6.0](https://github.com/Jin-Cheng-Ming/ZHKU-Connector/releases/download/1.6.0/ZHKU-Connector-windows-1.6.0.exe) |
| Linux | [linux-1.4](https://github.com/Jin-Cheng-Ming/ZHKU-Connector/releases/download/1.4/ZHKU-Connector)                     |
| mac   |                                                                                                                        |

> Linux需要将下载的文件设置为可执行文件，并在终端中运行。

## 🚧启动之前的环境搭建

在启动之前，需要下载一些依赖包，运行如下命令

```shell
pip install pyyaml  # 用于读取配置
pip install requests  # 用于向网页发送post请求
pip install pyquery  # 用于解析数据
pip install progress  # 用于说明检测状态
pip install termcolor  # 用于使输出的字符附带颜色的样式
pip install PyGithub  # 用于检查Github发行版的更新
```

或者根据依赖清单安装，运行如下命令

```shell
pip install -r requirements.txt
```

## 🍕如何启动

通过python命令启动，在所在文件夹内，运行如下命令

```shell
python Connector.py
```

如果环境里的有python3，也可以试试使用python3命令：

```shell
python3 Connector.py
```

~~也可以通过login文件运行：给login赋权后，就可以通过更简单的命令来运行了。
注意，如果环境是python3，那么需要将login里面的命令python改为python3~~

> 待更新

```shell
chmod 777 ./login # 赋权
./login # 启动
```

## ☘️保持后台运行

### Linux

在Linux操作系统中，如果有内置Screen软件的话，使用如下命令创建screen终端

```shell
screen
```

创建screen终端之后就可以再这个界面里面像上面一样的操作运行自动连接的程序。
当关闭shell终端之后，自动连接程序后台仍然保持运行。
通过如下命令来重新连接screen

```shell
screen -r
```

### Windows

> 待更新

```shell

```

## 🌞退出

在命令行中用 `Ctrl` + `C` 可以强制退出

