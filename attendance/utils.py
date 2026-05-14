import math

def haversine(lon1, lat1, lon2, lat2):
    """
    计算两点之间的球面距离（单位：米）
    参数：经度1, 纬度1, 经度2, 纬度2
    """
    # 将十进制度数转化为弧度
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # 经纬度差
    dlon = lon2 - lon1
    dlat = lat2 - lat1

    # 哈弗辛公式
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371000  # 地球平均半径，单位米

    return c * r