import streamlit as st
import requests
from serpapi import GoogleSearch

HF_TOKEN = st.secrets['HF_TOKEN']
SERPAPI_KEY = st.secrets['SERPAPI_KEY']

def normalize_query_with_llm(query):
    api_url = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": f"Normalize this product search: {query}"}
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        if response.ok:
            return response.json()[0]['generated_text']
    except Exception as e:
        print("LLM Error:", e)
    return query

def serpapi_search(query, site):
    params = {
        "engine": "google",
        "q": f"{query} site:{site}",
        "api_key": SERPAPI_KEY
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        # Try shopping_results first
        if "shopping_results" in results and results["shopping_results"]:
            item = results["shopping_results"][0]
            return {
                "title": item.get("title", "N/A"),
                "price": item.get("price", "N/A"),
                "url": item.get("link", "N/A")
            }

        # Fallback: Check organic_results and extract from rich_snippet
        for result in results.get("organic_results", []):
            title = result.get("title", "N/A")
            url = result.get("link", "N/A")
            price = "N/A"

            detected = result.get("rich_snippet", {}).get("bottom", {}).get("detected_extensions", {})
            if "price" in detected:
                price = f"${detected['price']}"
            elif "price_from" in detected and "price_to" in detected:
                price = f"${detected['price_from']} - ${detected['price_to']}"

            if price != "N/A":
                return {"title": title, "price": price, "url": url}

        return None
    except Exception as e:
        print(f"Error searching {site}: {e}")
        return None

def search_amazon(query): return serpapi_search(query, "amazon.com")
def search_walmart(query): return serpapi_search(query, "walmart.com")
def search_ebay(query): return serpapi_search(query, "ebay.com")

# --- Streamlit UI ---
st.title("🛒 Multi-Channel Price Comparator (Amazon, Walmart, eBay)")

item_title = st.text_input("Item Title")
upc = st.text_input("UPC")
asin = st.text_input("ASIN")
ean_gtin = st.text_input("EAN/GTIN")
use_llm = st.checkbox("Normalize Query with Free LLM (HuggingFace)", value=False)

if st.button("Search & Compare"):
    query = item_title or upc or asin or ean_gtin
    st.write(f"🔍 Searching for: `{query}`")

    if use_llm:
        query = normalize_query_with_llm(query)
        st.write(f"🧠 Normalized Query: `{query}`")

    amazon = search_amazon(query)
    walmart = search_walmart(query)
    ebay = search_ebay(query)

    st.markdown("### 💵 Price Comparison Table")
    st.markdown("| Platform | Title | Price | URL |")
    st.markdown("|----------|-------|-------|-----|")

    for name, result in [("Amazon", amazon), ("Walmart", walmart), ("eBay", ebay)]:
        if result:
            st.markdown(f"| {name} | {result['title']} | {result['price']} | [Link]({result['url']}) |")
        else:
            st.markdown(f"| {name} | Not found | - | - |")
