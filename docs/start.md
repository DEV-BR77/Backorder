cd C:\Development\Rückstände
python -m uvicorn app.main:app --reload

Dann im Browser öffnen:

http://127.0.0.1:8000

Falls python nicht gefunden wird:

C:\ProgramData\anaconda3\python.exe -m uvicorn app.main:app --reload
Wenn Port 8000 belegt ist, nutze beispielsweise Port 8001:

python -m uvicorn app.main:app --reload --port 8001
Dann: 

http://127.0.0.1:8001