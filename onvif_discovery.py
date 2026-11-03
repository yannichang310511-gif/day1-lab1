import socket

# ONVIF 標準的 WS-Discovery 多播位址與 Port
MULTICAST_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<Envelope xmlns:tds="http://onvif.org" '
    'xmlns="http://w3.org">'
    '<Header><MessageID>urn:uuid:68c8dfa5-f9be-4cfd-b3ef-888e400494bf</MessageID>'
    '<To>urn:schemas-xmlsoap-org:discorg:2006:02:discovery</To>'
    '<Action>http://xmlsoap-org.org</Action></Header>'
    '<Body><Probe><Types>tds:Device</Types></Probe></Body></Envelope>'
)

# 建立 UDP Socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.settimeout(3.0) # 設定超時時間

# 發送到 ONVIF 官方規定的多播群組 239.255.255.250，Port 3702
s.sendto(MULTICAST_XML.encode('utf-8'), ('239.255.255.250', 3702))

print("正在搜尋內網中的 ONVIF 設備...")
try:
    while True:
        data, addr = s.recvfrom(65535)
        print(f"發現 ONVIF 設備！ IP 位址: {addr[0]}")
        # data 裡面會包含該設備的詳細資訊（如 XAddr、網卡 MAC 等）
except socket.timeout:
    print("搜尋結束。")
