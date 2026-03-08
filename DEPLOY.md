# Oracle Cloud Always Free 배포 가이드

SKKU 공지 캘린더를 Oracle Cloud 무료 VM에 올리는 방법입니다.

---

## 1. Oracle Cloud 가입

1. [cloud.oracle.com](https://cloud.oracle.com) 접속 → **Start for free** 클릭
2. 국가, 이메일 입력 후 가입
3. **신용카드 등록** (검증용, Always Free만 쓰면 과금 없음)
4. 리전 선택 시 **서울** 있으면 서울 선택

---

## 2. Compute 인스턴스(VM) 만들기

1. 로그인 후 왼쪽 메뉴 **☰ → Compute → Instances**
2. **Create instance** 클릭

### 설정

| 항목 | 선택 |
|------|------|
| **Name** | `skku-calendar` (아무 이름이나 가능) |
| **Placement** | 기본값 |
| **Image and shape** | Edit 클릭 |
| **Image** | Ubuntu 22.04 |
| **Shape** | **Change shape** → **AMD** → `VM.Standard.E2.1.Micro` (Always free) 선택 |
| **Networking** | 기본 VCN, public IP 있음 확인 |
| **Add SSH keys** | **Generate a key pair for me** → **Save Private Key** 다운로드 (한 번만 가능!) |

3. **Create** 클릭

---

## 3. 방화벽(보안 목록) 열기

VM이 만들어지면 **Public IP**가 보입니다. 이 IP로 접속하려면 포트를 열어야 합니다.

1. **☰ → Networking → Virtual cloud networks**
2. 사용 중인 VCN 클릭 → **Security Lists** → **Default Security List**
3. **Add Ingress Rules** 클릭

| 항목 | 값 |
|------|-----|
| Source CIDR | `0.0.0.0/0` |
| Destination port range | `8000` |
| Description | `SKKU calendar app` |

4. **Add Ingress Rules** 저장  
5. (선택) SSH용으로 **22** 포트도 같은 방식으로 열어두기

---

## 4. VM에 SSH 접속

다운로드한 키 파일이 `skku-calendar.key`라고 가정합니다.

```bash
# Mac/Linux
chmod 400 skku-calendar.key
ssh -i skku-calendar.key ubuntu@<공인IP>
```

`<공인IP>`는 Oracle 콘솔의 Instance 상세에서 **Public IP**로 바꿉니다.  
Windows는 PuTTY나 Windows Terminal + `ssh -i` 사용하면 됩니다.

---

## 5. VM 안에서 앱 설치 및 실행

접속한 뒤 아래 명령을 순서대로 실행합니다.

```bash
# 시스템 업데이트 & Python, Git 설치
sudo apt update && sudo apt install -y python3-pip python3-venv git

# 프로젝트 클론 (본인 GitHub 주소로 변경)
git clone https://github.com/YOUR_USERNAME/NoticeCalender.git
cd NoticeCalender

# 가상환경 만들고 패키지 설치
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 바로 실행 테스트 (Ctrl+C로 종료)
python app.py
```

브라우저에서 `http://<공인IP>:8000` 으로 접속해 보이면 성공입니다.

---

## 6. 백그라운드 실행 (systemd)

VM을 끄거나 SSH를 끊어도 앱이 계속 돌게 하려면 systemd 서비스로 등록합니다.

```bash
# 서비스 파일 만들기
sudo nano /etc/systemd/system/skku-calendar.service
```

아래 내용을 **그대로** 붙여넣고, `YOUR_USERNAME`을 본인 Linux 사용자명(보통 `ubuntu`)으로 바꿉니다.

```ini
[Unit]
Description=SKKU Notice Calendar
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/NoticeCalender
Environment="PATH=/home/ubuntu/NoticeCalender/venv/bin"
ExecStart=/home/ubuntu/NoticeCalender/venv/bin/python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

저장: `Ctrl+O` → Enter → `Ctrl+X`

```bash
# 서비스 활성화 & 시작
sudo systemctl daemon-reload
sudo systemctl enable skku-calendar
sudo systemctl start skku-calendar
sudo systemctl status skku-calendar
```

`active (running)` 이면 정상입니다.

---

## 7. 접속 주소 정리

| 용도 | 주소 |
|------|------|
| 웹 캘린더 | `http://<공인IP>:8000` |
| ICS 피드 (구글 캘린더) | `http://<공인IP>:8000/feed.ics` |

Google Calendar 연동: 캘린더 → 다른 캘린더 → URL로 추가 → 위 ICS 주소 입력.

---

## 8. 나중에 코드 수정 반영하기

```bash
cd /home/ubuntu/NoticeCalender
git pull
sudo systemctl restart skku-calendar
```

---

## 문제 해결

- **접속이 안 될 때**: Security List에 8000 포트 추가했는지, VM이 실행 중인지 확인
- **앱이 죽을 때**: `sudo journalctl -u skku-calendar -f` 로 로그 확인
- **재부팅 후에도 실행**: `sudo systemctl enable skku-calendar` 한 번만 해두면 됨
