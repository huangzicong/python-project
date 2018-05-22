import asynchat,asyncore

#定义端口
PORT = 6666

#结束异常类
class Endsession(Exception):
    pass

class Chatserver(asyncore.dispatcher):
    #服务器
    def __init__(self,port):
        asyncore.dispatcher.__init__(self)
        #创建socket
        self.create_socket()
        #设置socke为可重用
        self.set_reuse_addr()
        #监听端口
        self.bind(('',port))
        self.listen(5)
        self.users = {}
        self.main_room = Chatserver(self)

    def handle_accept(self):
        conn,addr = self.accept()
        Chatsession(self,conn)

class Chatsession(asynchat.async_chat):
    #客户端通信
    def __init__(self,server,sock):
        asynchat.async_chat.__init__(self,sock)
        self.server = server
        self.set_terminator(b'\n')
        self.data = []
        self.name = None
        self.enter(Loginroom(server))

    def enter(self,room):
        #从当前房间移除自身，然后添加到指定房间
        try:
            cur = self.room
        except AttributeError:
            pass
        else:
            cur.remove(self)
        self.room = room
        room.add(self)

    def collect_incoming_data(self, data):
        #接受客户端的数据
        self.data.append(data.decode("utf-8"))
    def found_terminator(self):
        line = ''.join(self.data)
        self.data = []
        try:
            self.room.handle(self,line.encode("utf-8"))
            #退出聊天室
        except Endsession:
            self.handle_close()
    def handle_close(self):
        #当session关闭时，进入logoutroom
        asynchat.async_chat.handle_close(self)
        self.enter(LogoutRoom(self.server))


class CommandHandler:
    """
    命令处理类
    """
    def unknown(self,session,cmd):
        #响应未知命令
        #通过aynchat.async_chat.push方法发送信息
        session.push(('unknown command {} \n'.format(cmd)).encode("utf-8"))

    def handle(self,session,line):
        line = line.decode()
        #命令处理
        if not line.strip():
            return
        parts = line.split(' ',1)
        cmd = parts[0]
        try:
            line = parts[1].strip()
        except IndexError:
            line = ''

        #通过协议代码执行相应的方法
        method = getattr(self,'do_' + cmd,None)
        try:
            method(session,line)
        except TypeError:
            self.unknown(session,cmd)

class Room(CommandHandler):
    '''
    包含多个用户的环境，负责基本的命令处理和广播

    '''
    def __init__(self,server):
        self.server = server
        self.session = []

    def add(self,session):
        #一个用户进入房间
        self.session.append(session)

    def remove(self,session):
        #一个用户离开房间
        self.session.remove(session)

    def broadcast(self,line):
        #向所有的用户发送指定消息
        #使用asynchat.asyn_chat.push方法发送数据
        for session in self.session:
            session.push(line)

    def do_logout(self,session,line):
        #退出房间
        raise Endsession

class Loginroom(Room):
    """
    处理登录用户
    """
    def add(self,session):
        #用户连接成功的回应
        Room.add(self,session)
        # 使用 asynchat.asyn_chat.push 方法发送数据
        session.push(b'connect success')
    def do_login(self,session,line):
        #用户登录逻辑
        name = line.strip()
        #获取用户名称
        if not name:
            session.push(b'username empty')
        #检查是否有同名用户
        elif name in self.server.users:
            session.push(b'username exist')
        #检查成功，进入聊天室
        else:
            session.name = name
            session.enter(self.server.main_room)

class LogoutRoom(Room):
    """
    处理退出用户
    """

    def add(self, session):
        # 从服务器中移除
        try:
            del self.server.users[session.name]
        except KeyError:
            pass

class Chatroom(Room):
    '''
    聊天的房间

    '''
    def add(self,session):
        #广播新用户进入
        session.push(b'login success')
        self.broadcast((session.name + 'has enterd the room.\n').encode("utf-8"))
        self.server.users[session.name] = session
        Room.add(self,session)

    def remove(self,session):
        #广播用户离开
        Room.remove(self,session)
        self.broadcast((session.name + 'has left the room.\n').encode("utf-8"))

    def do_say(self,session,line):
        #查看在线用户
        session.push(b'online users')
        for other in self.session:
            session.push((other.name + line + '\n').encode("utf-8"))

if __name__ == '__main__':
    s = Chatserver(PORT)
    try:
        print("chat serve run at '0.0.0.0:{0}'".format(PORT))
        asyncore.loop()
    except KeyboardInterrupt:
        print("chat server exit")