# ZHKU-Connector

一个简单的仲恺农业工程学院校园网自动登录助手，还能在检测到失去互联网连接时自动登录。

![使用界面](img/img.png)

功能与特性：

- 账号认证登录
- 记住账号
- 互联网连接状态监测与自动登录
- 用户代理选择（电脑/手机）
- 多系统兼容（Windows/Linux/Mac）
- 内存占用低

已知问题与待办：

- 在海珠校区测试没有问题，白云校区没有做测试，兼容性未知，如果有需要可以提Issue
- 教师账号登录认证可能有点问题，因为没有账号测试，目前无法修复
- 不能手动下线


## ✨快速开始

下载打包好的应用程序直接运行即可

| 平台               | 下载                                                                                                               | MD5                              |
|--------------------|--------------------------------------------------------------------------------------------------------------------|----------------------------------|
| Windows            | [1.8.2](https://github.com/Jin-Cheng-Ming/ZHKU-Connector/releases/download/1.8.2/ZHKU-Connector-windows-1.8.2.exe) | fde6a8f82aaa9a9e5af02b5c3790ea82 |
| Linux(Ubuntu22.04) | [1.8.2](https://github.com/Jin-Cheng-Ming/ZHKU-Connector/releases/download/1.8.2/ZHKU-Connector-linux-1.8.2)       | 13b5230871931731c6db63f9634778da |
| Mac                |   暂无                                                                                                             |                                  |

> Linux需要将下载的文件设置为可执行文件，并在终端中运行。如：`chmod +x ZHKU-Connector-Linux-1.x.x`
> 在Windows的终端使用`certutil -hashfile <文件名> MD5`可以获取文件哈希值。
> 在Linux的终端中使用`md5sum <文件名>`可以获取文件哈希值。

## 🚧启动之前的环境搭建

在启动之前，需要下载一些依赖包，运行如下命令

```shell
pip install pyyaml  # 用于读取配置
pip install requests  # 用于向网页发送post请求
pip install pyquery  # 用于解析数据
pip install progress  # 用于说明检测状态
pip install termcolor  # 用于使输出的字符附带颜色的样式
pip install PyGithub  # 用于检查Github发行版的更新
pip install func_timeout  # 用户等待用户输入
```

或者根据依赖清单安装，运行如下命令

```shell
pip install -r requirements.txt
```

## 🍕如何启动

通过python命令启动，在所在文件夹内，运行如下命令

```shell
python ./src/Connector.py
```

如果环境里的有python3，也可以试试使用python3命令：

```shell
python3 ./src/Connector.py
```

不用python跑代码的话，也可以直接使用发行版直接启动：

在Windows中直接双击exe文件就可以启动了。

在Linux系统中，需要给文件先赋权，设置可执行，然后执行该文件即可。

```shell
chmod +x <文件名>
```

## ☘️保持后台运行

### Linux

在Linux操作系统中，如果有内置Screen软件的话，使用如下命令创建screen终端

```shell
screen
```

创建screen终端之后就可以再这个界面里面像上面一样的操作运行自动连接的程序。
当关闭shell终端之后，自动连接程序后台仍然保持运行。
也可以通过`ctrl`+`A` `D` 的快捷键离开（后台保持运行）。
通过如下命令来重新连接screen

```shell
screen -r
```

### Windows

> Windows的CMD不支持当前部分依赖库的日志颜色打印，建议使用Powershell或其他更现代的终端运行。也可以在微软商店中下载微软公司开发的“终端”，这里面有设置可以隐藏到状态栏

## 🌞退出

在命令行中用 `Ctrl` + `C` 可以强制退出

## 📑更新日志

[点击查看](./HISTORY.md)
