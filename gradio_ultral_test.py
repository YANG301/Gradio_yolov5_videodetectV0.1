# 在使用gradio prosess组件时不能使用代理，否则会报错Expecting value: line 1 column 1 (char 0)

import gradio as gr # gradio库
import cv2 as cv # cv图像处理库
import torch # 连接数据模型
import mysql.connector # 数据库连接
import pandas as pd # 图像与表格数据处理
from minio import Minio # 连接对象存储
from datetime import datetime # 获取时间
import time # 暂停
import uuid # 随机生成文件名
import os # 系统处理(主要用于文件处理)
import shutil # 删除文件夹所有内容
# import collections # 用于统计数据百分比
import json # 处理json数据
from configparser import ConfigParser # 导入配置文件

# 初始化数据
config = ConfigParser() # 实例化配置文件读取对象
config.read("./gradio.config") # 读配置文件
config_mysql = dict(config.items("mysql")) # 配置文件mysql section字典
config_minio = dict(config.items("minio")) # 配置文件minio section字典

model = torch.hub.load("./yolov5", "custom", path="./models/yolov5s.pt", source="local") # 初始加载模型



# 模型列表(读取项目models下的模型文件，读取后返回文件名列表)
def det_model():
    file_names = [] # 模型列表
    # 读取模型数据
    for file_name in os.listdir("./models"):
        file_names.append(file_name)
    # 返回模型列表
    return file_names
# 视频检测（调用图片检测实现）
def video_identity(request: gr.Request,video,progress=gr.Progress()):
    # 初始化参数
    localresults = None
    dirname = request.username + str(uuid.uuid4()) # 随机生成文件夹名
    filename = dirname + ".mp4" # 随机生成文件名
    detection_data = [] # 临时检测数据列表
    global detection_df # 全局线型图数据
    global label_data # 全局标签数据
    cap = cv.VideoCapture(video) # 将视频转换为cv对象
    fourcc = cv.VideoWriter_fourcc(*'MP4V') # 解码格式
    fps = cap.get(cv.CAP_PROP_FPS) # 视频帧率
    frames = cap.get(cv.CAP_PROP_FRAME_COUNT) # 视频帧数
    size = (int(cap.get(cv.CAP_PROP_FRAME_WIDTH)), # 视频尺寸
            int(cap.get(cv.CAP_PROP_FRAME_HEIGHT)))
    out = cv.VideoWriter('cache/det_videos/' + filename,fourcc,fps,size) # 输出视频路径
    os.makedirs('cache/det_imgs/'+dirname) # 创建图片缓存文件夹

    # 进度条初始化
    progress(0,desc="Starting...") # 进度条设置为0
    time.sleep(1) # 延时1秒

    # 视频检测
    for i in progress.tqdm(range(int(frames))): # 每检测一个视频帧，进度加一
        ret,frame = cap.read() # 初始化视频的参数
        if i%fps == 0:
            localresults = None
            localresults = model(frame) # 获取检测的数据
            frame = localresults.render()[0] # 标注当前帧
            cv.imwrite("cache/det_imgs/"+dirname+"/"+str(i)+'.png',frame) #标注后的结果存为图片
            for result in localresults.pandas().xyxy[0].to_dict(orient='records'): # 循环获得一帧中的检测数据
                label = result['name']  # 标签名
                count = sum(1 for r in localresults.pandas().xyxy[0].to_dict(orient='records') if r['name'] == label) # 统计当前标签在检测结果中出现的数量
                # 检测数据返回格式
                detection = {
                    'frame': i,
                    'class': label,
                    'num': count
                }
                # 将数据添加进临时检测数据列表
                detection_data.append(detection)
        else:
            localresults.ims[0] = frame
            frame = localresults.render()[0]
            cv.imwrite("cache/det_imgs/"+dirname+"/"+str(i)+'.png',frame) #标注后的结果存为图
    
    # 线型图数据
    detection_data = [dict(t) for t in {tuple(d.items()) for d in detection_data}] # 转化数据
    detection_data = sorted(detection_data, key=lambda x: x['frame']) #清除重复数据
    detection_df = pd.DataFrame(detection_data,columns=['frame','num','class']) # 将数据转换为pandas的DataFrame格式

    # 标签数据
    # 统计每个标签的数量
    label_counts = {}
    for item in detection_data:
        label = item['class']
        num = item['num']
        if label in label_counts:
            label_counts[label] += num
        else:
            label_counts[label] = num
    # 计算每个标签的百分比
    print(label_counts)
    total_samples = sum(label_counts.values())
    label_data = {label: count / total_samples for label, count in label_counts.items()}
    print(label_data)

    # 将检测后的图片组合为视频
    for i in range(int(frames)):
        img = cv.imread("cache/det_imgs/"+dirname+"/"+str(i)+'.png')
        out.write(img)

    # 释放资源
    cap.release() # 释放视频资源
    shutil.rmtree("cache/det_imgs/"+dirname) # 删除cache图片文件夹的缓存数据
    return "cache/det_videos/"+filename #返回视频路径
# 线型图数据展示
def line_plot_fn(data):
    if data:
        return gr.LinePlot.update(
            detection_df,
            x="frame",
            y="num",
            color="class",
            title="标注数据",
            tooltip=['frame', 'num', 'class'],
            height=500,
            width=1000
        )
# 散点图数据展示
def scatter_plot_fn(data):
    if data:
        return gr.ScatterPlot.update(
            detection_df,
            x="frame",
            y="num",
            color="class",
            title="标注数据",
            tooltip=['frame', 'num', 'class'],
            height=500,
            width=1000
        )
# 标签数据展示
def lable_fn(data):
    if data:
        return label_data
# 连接对象数据库（上传视频）
def upload_video(request: gr.Request,video):
    if video==None or video=="":
        return("""<p align="right">""" + "视视频未标注，请标注后上传"+"</p>")
    else:
        # 创建Minio客户端实例
        client = Minio(
            config_minio.get('address'),  # MinIO服务器的地址和端口
            access_key=config_minio.get('access_key'),  # 访问密钥
            secret_key=config_minio.get('secret_key'),  # 秘密访问密钥
            secure=False  # 如果未启用TLS/SSL，请将此参数设置为False；如果启用了TLS/SSL，请设置为True
        )

        # 上传视频文件
        bucket_name = config_minio.get('bucket_name')
        file_path = "cache/det_videos/"+os.path.basename(video)

        uname = request.username
        name = datetime.now().strftime("%Y%m%d%H%M%S")
        create_time = datetime.now()
        json_data = detection_df.to_json(orient='records')
        object_name = os.path.basename(video)

        # 执行上传操作
        client.fput_object(
            bucket_name,
            object_name,
            file_path,
        )

        # 连接到MySQL数据库
        connection = mysql.connector.connect(
            host=config_mysql.get('host'),
            port=config_mysql.get('port'),
            user=config_mysql.get('user'),
            password=config_mysql.get('password'),
            database=config_mysql.get('database')
        )

        # 创建游标对象
        cursor = connection.cursor()

        #数据库插入数据
        insert_query = "INSERT INTO datas (uname, name, create_time, chart_data, video_url) VALUES (%s, %s, %s, %s, %s)"
        insert_values = (uname, name, create_time, json_data, object_name)
        cursor.execute(insert_query, insert_values)

        # 提交更改
        connection.commit()

        # 关闭游标和连接
        cursor.close()
        connection.close()
        os.remove(file_path)
        return("""<p align="right">"""+name+"视频数据上传成功"+"</p>")
# 数据库连接（查询用户）
def sql_connection(username,password):
    # 连接到数据库
    connection = mysql.connector.connect(
        host=config_mysql.get('host'),
        port=config_mysql.get('port'),
        user=config_mysql.get('user'),
        password=config_mysql.get('password'),
        database=config_mysql.get('database')
    )

    # 在连接上执行操作
    cursor = connection.cursor()
    cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()

    # 检查用户名是否存在以及密码是否匹配
    if result and result[0] == password:
        cursor.close()
        connection.close()
        return True
    else:
        cursor.close()
        connection.close()
        return False
# 数据库连接（查询数据-视频）
def get_datas(request: gr.Request):
    # 连接到数据库
    connection = mysql.connector.connect(
        host=config_mysql.get('host'),
        port=config_mysql.get('port'),
        user=config_mysql.get('user'),
        password=config_mysql.get('password'),
        database=config_mysql.get('database')
    )

    # 在连接上执行操作
    cursor = connection.cursor()
    cursor.execute("SELECT name,create_time,video_url FROM datas WHERE uname = %s",(request.username,))
    results = cursor.fetchall()

    # 处理结果并转换为列表格式的元组
    data = []
    for row in results:
        data.append(list(row))

    # 关闭连接
    cursor.close()
    connection.close()
    return data
# 更新用户名
def update_username(request: gr.Request):
    return "User:"+request.username
# 获取数据库的视频
def get_video(list,evt:gr.SelectData):
    # 创建Minio客户端实例
    client = Minio(
        config_minio.get('address'),  # MinIO服务器的地址和端口
        access_key=config_minio.get('access_key'),  # 访问密钥
        secret_key=config_minio.get('secret_key'),  # 秘密访问密钥
        secure=False  # 如果未启用TLS/SSL，请将此参数设置为False；如果启用了TLS/SSL，请设置为True
    )
    bucket_name = config_minio.get('bucket_name')
    object_name = list.values.tolist()[evt.index[0]][2]
    file_path = "cache/dowload_videos/" + object_name  # 替换为你想保存视频的路径

    try:
        client.fget_object(bucket_name, object_name, file_path)
    except Exception as e:
        print("下载视频失败:", str(e))
        return None

    return file_path
# 获取展示的json数据
def get_plot(list,evt:gr.SelectData,request: gr.Request):
    object_name = list.values.tolist()[evt.index[0]][2]
    global data_df

    # 连接到数据库
    connection = mysql.connector.connect(
        host=config_mysql.get('host'),
        port=config_mysql.get('port'),
        user=config_mysql.get('user'),
        password=config_mysql.get('password'),
        database=config_mysql.get('database')
    )

    # 在连接上执行操作
    cursor = connection.cursor()
    cursor.execute("SELECT chart_data FROM datas WHERE uname = %s AND video_url = %s",(request.username,object_name))
    jsonresults = json.loads(cursor.fetchone()[0])
    data_df = pd.DataFrame(jsonresults,columns=['frame','num','class'])

    # 关闭连接
    cursor.close()
    connection.close()
    return gr.LinePlot.update(
        data_df,
        x="frame",
        y="num",
        color="class",
        # color_legend_position="bottom",
        title="标注数据",
        tooltip=['frame', 'num', 'class'],
        height=500,
        width=1000
    )
# 切换模型
def switch_model(evt:gr.SelectData):
    model = torch.hub.load("./yolov5", "custom", path="./models/"+evt.value, source="local")
    return """<p align="right">"""+evt.value+"模型加载成功！"+"</p>"

# 前端界面渲染
with gr.Blocks() as demo:
    with gr.Row():
        user_name = gr.Markdown()
        status = gr.Markdown()
    with gr.Tabs():
        with gr.TabItem("标注"):
            with gr.Row():
                video_input = gr.Video()
                video_output = gr.Video()
            with gr.Row():
                video_button = gr.Button("Submit")
                upload_button = gr.Button("Upload")
            model_select = gr.Dropdown(det_model(), label="模型", info="模型从本地文件读取，选择你的模型",value="yolov5s.pt")
            label = gr.Label()
            with gr.Tabs():
                with gr.TabItem("线性图"):
                    lineplot = gr.LinePlot(show_label=False).style(container=False)
                with gr.TabItem("散点图"):
                    scatterplot = gr.ScatterPlot(show_label=False).style(container=False)
        with gr.TabItem("展示") as tab_b:
            video_show = gr.Video()
            line_show = gr.LinePlot()
            with gr.Row():
                video_list = gr.Dataframe(
                    value=get_datas(request=gr.Request()),
                    headers=["项目名","上传时间","文件名"],
                    datatype=["str","str","str"],
                    interactive=False
                )
    video_button.click(video_identity,inputs=video_input,outputs=video_output)
    upload_button.click(upload_video,inputs=video_output,outputs=status)
    video_output.change(line_plot_fn,inputs=video_output,outputs=lineplot,show_progress=True)
    video_output.change(scatter_plot_fn,inputs=video_output,outputs=scatterplot,show_progress=True)
    video_output.change(lable_fn,inputs=video_output,outputs=label,show_progress=True)
    video_list.select(fn = get_video,inputs=video_list,outputs = video_show)
    video_list.select(fn = get_plot,inputs=video_list,outputs = line_show)
    model_select.select(switch_model,inputs=None,outputs=status)
    tab_b.select(fn = get_datas,outputs=video_list)
    demo.load(update_username,inputs=None,outputs=user_name)

if __name__ == "__main__":
    demo.queue().launch(auth=sql_connection,auth_message="Hi,注册功能还未开发")