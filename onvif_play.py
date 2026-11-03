import cv2
from onvif import ONVIFCamera

# ==================== 設定區 ====================
IP = "192.168.0.94"      # 攝影機的內網 IP
PORT = 80                 # ONVIF 連接埠 (通常是 80, 8888 或 80
USER = "admin"            # 攝影機的 ONVIF 帳號
PASSWORD = "bb960308" # 攝影機的 ONVIF 密碼
RTSP_URL = "rtsp://192.168.0.94:554/onvif1"  # 已知的直接串流網址
# ===============================================

def get_rtsp_url():
    # 已知 RTSP 網址時直接使用，不再連線至 ONVIF HTTP 服務。
    if RTSP_URL:
        print("使用已設定的 RTSP 網址連線...")
        if USER and PASSWORD and "@" not in RTSP_URL:
            return RTSP_URL.replace("rtsp://", f"rtsp://{USER}:{PASSWORD}@", 1)
        return RTSP_URL

    try:
        print("正在透過 ONVIF 連線至攝影機...")
        # 初始化 ONVIF 連線 (需要指定 wsdl 檔案路徑，套件內建通常會自動配對)
        cam = ONVIFCamera(IP, PORT, USER, PASSWORD)
        
        # 建立媒體服務 (Media Service)
        media_service = cam.create_media_service()
        
        # 獲取攝影機的所有設定檔 (Profiles)
        # 概念：通常 Profile[0] 是高畫質(主碼流)，Profile[1] 是低畫質(子碼流)
        profiles = media_service.GetProfiles()
        if not profiles:
            print("錯誤：找不到任何 Media Profile。")
            return None
            
        target_profile = profiles[0]
        print(f"成功獲取 Profile: {target_profile.Name} (Token: {target_profile.token})")
        
        # 設定索取串流網址的參數
        request_options = media_service.create_type('GetStreamUri')
        request_options.ProfileToken = target_profile.token
        request_options.StreamSetup = {
            'Stream': 'RTP-Unicast',
            'Transport': {'Protocol': 'RTSP'}
        }
        
        # 向攝影機要求 RTSP URL
        uri_response = media_service.GetStreamUri(request_options)
        rtsp_url = uri_response.Uri
        
        # 有些攝影機回傳的 URL 不包含帳密，手動將帳密嵌入 RTSP 網址中以防驗證失敗
        if f"{USER}:{PASSWORD}@" not in rtsp_url:
            rtsp_url = rtsp_url.replace("rtsp://", f"rtsp://{USER}:{PASSWORD}@")
            
        return rtsp_url

    except Exception as e:
        print(f"ONVIF 連線或獲取 URL 失敗: {e}")
        return None

def show_camera_view(rtsp_url):
    safe_url = rtsp_url.replace(f":{PASSWORD}@", ":******@") if PASSWORD else rtsp_url
    print(f"正在拉取串流影像，網址: {safe_url}")
    
    # 透過 OpenCV 開啟 RTSP 影像串流
    cap = cv2.VideoCapture(rtsp_url)
    
    if not cap.isOpened():
        print("錯誤：無法開啟影像串流，請檢查網路、RTSP 埠(554) 或 H.264/H.265 編碼設定。")
        return

    print("成功連線！正在顯示畫面，請按 'Q' 鍵退出...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("訊號中斷，嘗試重新讀取中...")
            continue
            
        # 縮放畫面大小（選填，避免 4K 畫面太大超出螢幕）
        display_frame = cv2.resize(frame, (1280, 720))
        
        # 顯示視窗畫面
        cv2.imshow("ONVIF Camera Live View", display_frame)
        
        # 偵測鍵盤事件，按下 'q' 或 'Q' 結束
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 釋放資源
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    url = get_rtsp_url()
    if url:
        show_camera_view(url)
