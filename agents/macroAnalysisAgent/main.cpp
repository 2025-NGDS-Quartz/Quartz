#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>
#include <thread>
#include <chrono> 
#include <cstdlib>  
#include <fstream>
#include <ctime>
#include <iomanip>

#include <curl/curl.h>
#include <nlohmann/json.hpp>

#include "S3Uploader.h"

#ifdef _WIN32
#include <windows.h> 
#endif

using json = nlohmann::json;
using namespace std;

// 메모리 콜백 & HTTP 요청
size_t WriteCallback(void* contents, size_t size, size_t nmemb, void* userp) {
    ((string*)userp)->append((char*)contents, size * nmemb);
    return size * nmemb;
}

// 현재 날짜, 시각 반환 (YYYYMMDDhhmmss)
string getCurrentTimestamp() {
    auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    std::stringstream ss;
    ss << std::put_time(std::localtime(&now), "%Y%m%d%H%M%S"); 
    return ss.str();
}

// 요청
string performRequest(const string& url, const vector<string>& headers = {}, const string& postData = "", int max_retries = 3) {
    long http_code = 0;

    for (int i = 0; i < max_retries; ++i) {
        CURL* curl = curl_easy_init();
        string readBuffer;

        if (curl) {
            struct curl_slist* chunk = NULL;
            for (const auto& header : headers) {
                chunk = curl_slist_append(chunk, header.c_str());
            }

            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);
            curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 0L);

            if (chunk) curl_easy_setopt(curl, CURLOPT_HTTPHEADER, chunk);

            if (!postData.empty()) {
                curl_easy_setopt(curl, CURLOPT_POST, 1L);
                curl_easy_setopt(curl, CURLOPT_POSTFIELDS, postData.c_str());
            }

            CURLcode res = curl_easy_perform(curl);
            if (res == CURLE_OK) {
                curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);
            }

            curl_easy_cleanup(curl);
            if (chunk) curl_slist_free_all(chunk);

            // 응답이 200이면 리턴
            if (res == CURLE_OK && http_code == 200) {
                return readBuffer;
            }
            // 응답 실패
            else if (res == CURLE_OK && http_code != 200) {
                cerr << "\n[Gemini API Error] HTTP Status Code: " << http_code << endl;
                cerr << "Error Message from Google: " << readBuffer << endl;
                return ""; 
            }
        }

        this_thread::sleep_for(chrono::seconds(1));
    }
    return "";
}

// ECOS 데이터 수집 전용 함수
vector<pair<string, string>> fetchEcosData(string key, string table, string item, string start, string end) {
    string url = "https://ecos.bok.or.kr/api/StatisticSearch/" + key + "/json/kr/1/100/" +
        table + "/M/" + start + "/" + end + "/" + item;

    vector<pair<string, string>> results;
    string resp = performRequest(url);

    if (resp.empty()) return results;

    try {
        json j = json::parse(resp);
        // ECOS 에러 체크
        if (j.contains("RESULT")) return results;

        if (j.contains("StatisticSearch") && j["StatisticSearch"].contains("row")) {
            for (auto& row : j["StatisticSearch"]["row"]) {
                string date = row["TIME"].get<string>();
                string val = row["DATA_VALUE"].get<string>();
                results.push_back({ date, val });
            }
        }
    }
    catch (...) {
        cerr << "ECOS Parsing Error" << endl;
    }

    // API 과부화 방지
    this_thread::sleep_for(chrono::milliseconds(100));
    
    return results;
}

// Gemini 보고서 생성
string generateGeminiReport(const string& csv_data, const string& type, const string& api_key) {
    string gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=" + api_key;

    string prompt_text;
    if (type == "positive") {
        prompt_text = "Act as an optimistic economist. Based on the Korean economic data below, write a report highlighting growth opportunities, stability, and recovery signs. Format as a professional markdown report.\n[Data]\n" + csv_data;
    }
    else {
        prompt_text = "Act as a risk management analyst. Based on the Korean economic data below, write a report focusing on inflation risks, debt burden, and currency volatility. Warn about potential recession scenarios.\n[Data]\n" + csv_data;
    }

    json payload;
    payload["contents"] = json::array({ { {"parts", json::array({ {{"text", prompt_text}} })} } });
    payload["generationConfig"] = { {"temperature", 0.4} };

    vector<string> headers = { "Content-Type: application/json" };
    string resp = performRequest(gemini_url, headers, payload.dump());

    try {
        json j = json::parse(resp);
        if (j.contains("candidates")) {
            return j["candidates"][0]["content"]["parts"][0]["text"];
        }
    }
    catch (...) { cerr << "Gemini Parsing Error" << endl; }

    return "";
}

// 핵심 로직 함수
void run_analysis() {
    // 윈도우 콘솔 한글 설정
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif

    // 환경 변수에서 키 가져오기
    const char* ecos_env = getenv("MY_ECOS_KEY");
    const char* gemini_env = getenv("MY_GEMINI_KEY");

    if (!ecos_env || !gemini_env) {
        cerr << "[Error] 환경 변수 MY_ECOS_KEY 또는 MY_GEMINI_KEY가 설정되지 않았습니다." << endl;
        return;
    }

    string ecos_key = ecos_env;
    string gemini_key = gemini_env;

    // 기간 설정 (2023년 1월 ~ 2025년 12월)
    string start_date = "202301";
    string end_date = "202512";

    cout << "=== Fetching Macroeconomic Data from ECOS ===" << endl;

    // 5개 지표 수집
    // (1) 기준금리 (722Y001 / 0101000)
    auto rates = fetchEcosData(ecos_key, "722Y001", "0101000", start_date, end_date);
    cout << "1. 기준금리: " << rates.size() << " months fetched." << endl;

    // (2) 근원물가 (901Y010 / DB: 식료품 및 에너지 제외)
    auto cpis = fetchEcosData(ecos_key, "901Y010", "DB", start_date, end_date);
    cout << "2. 근원물가: " << cpis.size() << " months fetched." << endl;

    // (3) 환율 (731Y004 / 0000001: 원-달러 / 0000100: 평균자료)
    auto exchange = fetchEcosData(ecos_key, "731Y004", "0000001/0000100", start_date, end_date);
    cout << "3. 원-달러 환율: " << exchange.size() << " months fetched." << endl;

    // (4) 수출입 총괄 (901Y118 / T002:수출, T004:수입)
    auto exports = fetchEcosData(ecos_key, "901Y118", "T002", start_date, end_date);
    auto imports = fetchEcosData(ecos_key, "901Y118", "T004", start_date, end_date);
    cout << "4. 수출입 총괄: " << exports.size() << " months fetched." << endl;

    // (5) 가계대출 (151Y005 / 11110A0: 주택담보대출-예금은행)
    auto loans = fetchEcosData(ecos_key, "151Y005", "11110A0", start_date, end_date);
    cout << "5. 가계대출: " << loans.size() << " months fetched." << endl;

    // 데이터 정렬 (최소 길이 기준)
    size_t min_len = rates.size();
    min_len = min(min_len, cpis.size());
    min_len = min(min_len, exchange.size());
    min_len = min(min_len, exports.size());
    min_len = min(min_len, imports.size());
    min_len = min(min_len, loans.size());

    if (min_len == 0) {
        cerr << "[Error] 데이터를 가져오는데 실패했습니다. ECOS 키나 인터넷 연결을 확인하세요." << endl;
        return;
    }

    // CSV 프롬프트 생성
    stringstream ss;
    ss << "Date, BaseRate(%), CoreCPI(2020=100), USD/KRW(Avg), Export(Mil$), Import(Mil$), MortgageLoan(Bil KRW)\n";

    for (size_t i = 0; i < min_len; ++i) {
        ss << rates[i].first << ", "
            << rates[i].second << ", "
            << cpis[i].second << ", "
            << exchange[i].second << ", "
            << exports[i].second << ", "
            << imports[i].second << ", "
            << loans[i].second << "\n";
    }

    string csv_data = ss.str();

    // Gemini API 호출
    cout << "\n=== Sending Data to Gemini ===" << endl;

    // 버킷 이름
    const char* bucket_name = "quartz-bucket";
    S3Uploader uploader("ap-northeast-2");

    cout << "\nGenerating & Uploading Reports..." << endl;

    // 긍정 보고서
    cout << "   - Generating Positive Report..." << endl;
    string pos_report = generateGeminiReport(csv_data, "positive", gemini_key);
    if (!pos_report.empty()) {
        string fname = "Report_Positive_" + end_date + ".md";
        if (uploader.uploadFile(bucket_name, fname, pos_report)) {
            cout << "   [Success] Uploaded: " << fname << endl;
        }
    }

    // 부정 보고서
    cout << "   - Generating Negative Report..." << endl;
    string neg_report = generateGeminiReport(csv_data, "negative", gemini_key);
    if (!neg_report.empty()) {
        string fname = "Report_Negative_" + end_date + ".md";
        if (uploader.uploadFile(bucket_name, fname, neg_report)) {
            cout << "   [Success] Uploaded: " << fname << endl;
        }
    }
}

int main() {
    cout << "프로그램 시작" << endl;
    run_analysis();
    cout << "프로그램 종료" << endl;

    return 0;
}