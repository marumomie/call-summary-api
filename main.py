# Bubbleに保存
    async with httpx.AsyncClient() as http:
        response = await http.post(
            f"https://{BUBBLE_APP_ID}.bubbleapps.io/version-test/api/1.1/obj/callnote",
            headers={
                "Authorization": f"Bearer {BUBBLE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "title": title,
                "summary": summary_text,
                "transcript": input.text,
                "color": "yellow"
            }
        )
        print(f"Bubble response: {response.status_code}")
        print(f"Bubble body: {response.text}")