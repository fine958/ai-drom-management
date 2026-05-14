import base64, pyperclip

with open('C:/Users/27954/Desktop/R-C.jpg', 'rb') as f:
    img_base64 = base64.b64encode(f.read()).decode()

pyperclip.copy(img_base64)
print("base64 已复制到剪贴板，直接粘贴到 Postman 即可")