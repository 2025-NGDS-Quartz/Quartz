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

// HTTP 요청 (GET/POST 공용)
string performRequest(const string& url,
                      const vector<string>& headers = {},
                      const string& postData = "",
                      int max_retries = 3) {
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
                cerr << "\n[HTTP Error] HTTP Status Code: " << http_code << endl;
                cerr << "Response: " << readBuffer << endl;
                return "";
            }
        }

        this_thread::sleep_for(chrono::seconds(1));
    }
    return "";
}

// 현재 날짜, 시각 반환 (YYYYMMDD_hhmmss)
string getCurrentTimestamp() {
    auto now = std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());
    std::stringstream ss;
    ss << std::put_time(std::localtime(&now), "%Y%m%d_%H%M%S");
    return ss.str();
}

// ===== ECOS 데이터 수집 =====
vector<pair<string, string>> fetchEcosData(string key,
                                           string table,
                                           string item,
                                           string start,
                                           string end) {
    string url = "https://ecos.bok.or.kr/api/StatisticSearch/" + key +
                 "/json/kr/1/100/" + table + "/M/" + start + "/" + end + "/" + item;

    vector<pair<string, string>> results;
    string resp = performRequest(url);

    if (resp.empty()) return results;

    try {
        json j = json::parse(resp);
        // ECOS 에러 체크
        if (j.contains("RESULT")) return results;

        if (j.contains("StatisticSearch") &&
            j["StatisticSearch"].contains("row")) {
            for (auto& row : j["StatisticSearch"]["row"]) {
                string date = row["TIME"].get<string>();
                string val  = row["DATA_VALUE"].get<string>();
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

// ===== FRED 데이터 수집 =====
// seriesId 예시: "FEDFUNDS", "CPIAUCSL"
vector<pair<string, string>> fetchFredSeries(const string& fredKey,
                                             const string& seriesId,
                                             const string& startDate, // "YYYY-MM-DD"
                                             const string& endDate) {  // "YYYY-MM-DD"
    vector<pair<string, string>> results;

    string url = "https://api.stlouisfed.org/fred/series/observations"
                 "?series_id=" + seriesId +
                 "&api_key=" + fredKey +
                 "&file_type=json"
                 "&observation_start=" + startDate +
                 "&observation_end=" + endDate;

    string resp = performRequest(url);
    if (resp.empty()) return results;

    try {
        json j = json::parse(resp);
        if (j.contains("observations") && j["observations"].is_array()) {
            for (auto& ob : j["observations"]) {
                string date  = ob.value("date", "");
                string value = ob.value("value", "");
                if (!date.empty() && !value.empty() && value != ".") {
                    results.push_back({ date, value });
                }
            }
        }
    }
    catch (...) {
        cerr << "FRED Parsing Error" << endl;
    }

    this_thread::sleep_for(chrono::milliseconds(100));
    return results;
}

// ===== World Bank Indicators 데이터 수집 =====
// country: "WLD", "USA", "KOR" 등 ISO3
// indicator: 예) "NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG"
vector<pair<string, string>> fetchWorldBankSeries(const string& country,
                                                  const string& indicator,
                                                  const string& startYear, // "YYYY"
                                                  const string& endYear) { // "YYYY"
    vector<pair<string, string>> results;

    string url = "https://api.worldbank.org/v2/country/" + country +
                 "/indicator/" + indicator +
                 "?date=" + startYear + ":" + endYear +
                 "&format=json&per_page=2000";

    string resp = performRequest(url);
    if (resp.empty()) return results;

    try {
        json j = json::parse(resp);
        // 응답 구조: [ meta, [ { "date": "2024", "value": 3.5, ... }, ... ] ]
        if (j.size() >= 2 && j[1].is_array()) {
            for (auto& row : j[1]) {
                if (row["value"].is_null()) continue;

                string year = row.value("date", "");
                if (year.empty()) continue;

                string value;
                if (row["value"].is_number()) {
                    value = to_string(row["value"].get<double>());
                } else {
                    value = row["value"].get<string>();
                }

                results.push_back({ year, value });
            }
        }
    }
    catch (...) {
        cerr << "World Bank Parsing Error" << endl;
    }

    this_thread::sleep_for(chrono::milliseconds(100));
    return results;
}

// ===== Gemini 3 Grounded 보고서 생성 =====
string generateGeminiReport(const string& csv_data,
                            const string& type,
                            const string& api_key) {
    // Gemini 3 Pro preview + Google Search grounding
    string gemini_url =
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3-pro-preview:generateContent";

    string role_instruction;
    if (type == "positive") {
        role_instruction =
            "You are an optimistic macroeconomist. "
            "Focus on growth opportunities, resilience, and soft-landing scenarios.";
    } else {
        role_instruction =
            "You are a risk-focused macro strategist. "
            "Focus on inflation risks, debt overhang, external vulnerability, "
            "and hard-landing scenarios.";
    }

    string prompt_text =
        role_instruction +
        " Use ONLY data trends provided below plus grounded information from Google Search."
        " Combine Korean macro data (ECOS), US macro data (FRED), and global indicators (World Bank). "
        "Write a professional markdown report in Korean, including:\n"
        "- 개요 (현재 세계/한국 거시환경 요약)\n"
        "- 한국(금리, 물가, 환율, 수출입, 가계부채)에 대한 평가\n"
        "- 미국 및 주요국(금리, 물가, 성장)에 대한 평가\n"
        "- 시나리오별(낙관/기준/비관) 시장 영향과 자산별(주식, 채권, 환율) 함의\n"
        "- 포트폴리오 관점에서의 시사점\n\n"
        "[DATA]\n" + csv_data;

    json payload;
    payload["contents"] = json::array({
        json{
            { "parts", json::array({
                json{ { "text", prompt_text } }
            }) }
        }
    });

    json genCfg;
    genCfg["temperature"] = 0.4;
    // reasoning 레벨은 low로 설정 (필요시 high로 변경 가능)
    genCfg["thinkingConfig"] = { { "thinkingLevel", "low" } };
    payload["generationConfig"] = genCfg;

    // Google Search grounding 활성화
    payload["tools"] = json::array({
        json{ { "google_search", json::object() } }
    });

    vector<string> headers = {
        "Content-Type: application/json",
        "x-goog-api-key: " + api_key
    };

    string resp = performRequest(gemini_url, headers, payload.dump());

    try {
        json j = json::parse(resp);
        if (j.contains("candidates") && !j["candidates"].empty()) {
            auto& c0 = j["candidates"][0];
            if (c0.contains("content") &&
                c0["content"].contains("parts") &&
                !c0["content"]["parts"].empty() &&
                c0["content"]["parts"][0].contains("text")) {
                return c0["content"]["parts"][0]["text"].get<string>();
            }
        }
    }
    catch (...) {
        cerr << "Gemini 3 Parsing Error" << endl;
    }

    return "";
}

// ===== Gemini 3 보고서 요약 (10문장이내) =====
string summarizeReport(const string& full_report,
                       const string& type,
                       const string& api_key) {
    string gemini_url =
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3-pro-preview:generateContent";

    string prompt_text;
    if (type == "positive") {
        prompt_text =
            "다음의 거시경제 긍정 보고서를 한국어로 10문장이내로 요약해줘. "
            "핵심 성장 모멘텀, 정책 여력, 리스크 완화 요인에 집중해. "
            "추가 설명 없이 요약문만 출력해.\n\n[Report]\n" + full_report;
    } else {
        prompt_text =
            "다음의 거시경제 리스크 보고서를 한국어로 10문장이내로 요약해줘. "
            "핵심 리스크, 취약 구간, 꼬리위험(tail risk)에 집중해. "
            "추가 설명 없이 요약문만 출력해.\n\n[Report]\n" + full_report;
    }

    json payload;
    payload["contents"] = json::array({
        json{
            { "parts", json::array({
                json{ { "text", prompt_text } }
            }) }
        }
    });

    json genCfg;
    genCfg["temperature"] = 0.3;
    genCfg["thinkingConfig"] = { { "thinkingLevel", "low" } };
    payload["generationConfig"] = genCfg;

    vector<string> headers = {
        "Content-Type: application/json",
        "x-goog-api-key: " + api_key
    };

    string resp = performRequest(gemini_url, headers, payload.dump());

    try {
        json j = json::parse(resp);
        if (j.contains("candidates") && !j["candidates"].empty()) {
            auto& c0 = j["candidates"][0];
            if (c0.contains("content") &&
                c0["content"].contains("parts") &&
                !c0["content"]["parts"].empty() &&
                c0["content"]["parts"][0].contains("text")) {
                return c0["content"]["parts"][0]["text"].get<string>();
            }
        }
    }
    catch (...) {
        cerr << "Gemini 3 Summarize Parsing Error" << endl;
    }

    return "";
}

// ===== 핵심 로직 =====
void run_analysis() {
    // 윈도우 콘솔 한글 설정
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
#endif

    // 환경 변수에서 키 가져오기
    const char* ecos_env   = getenv("ECOS_API_KEY");
    const char* gemini_env = getenv("GEMINI_API_KEY");
    const char* fred_env   = getenv("FRED_API_KEY");

    if (!ecos_env) {
        cerr << "[Error] 환경 변수 ECOS_API_KEY가 설정되지 않았습니다." << endl;
        return;
    }
    if (!gemini_env) {
        cerr << "[Error] 환경 변수 GEMINI_API_KEY가 설정되지 않았습니다." << endl;
        return;
    }
    if (!fred_env) {
        cerr << "[Warning] FRED_API_KEY가 설정되지 않아 미국 지표는 생략됩니다." << endl;
    }

    string ecos_key   = ecos_env;
    string gemini_key = gemini_env;
    string fred_key   = fred_env ? string(fred_env) : "";

    // 기간 설정
    string start_date = "202301";  // ECOS 월별
    string end_date   = "202512";

    // FRED: 월별 관측 커버용
    string fred_start = "2023-01-01";
    string fred_end   = "2025-12-31";

    // World Bank: 연도
    string wb_start_year = "2023";
    string wb_end_year   = "2025";

    cout << "=== Fetching Macroeconomic Data (ECOS / FRED / World Bank) ===" << endl;

    // (1) 한국 ECOS 5개 지표
    auto rates    = fetchEcosData(ecos_key, "722Y001", "0101000", start_date, end_date);
    cout << "1. 기준금리: " << rates.size() << " months fetched." << endl;

    auto cpis     = fetchEcosData(ecos_key, "901Y010", "DB", start_date, end_date);
    cout << "2. 근원물가: " << cpis.size() << " months fetched." << endl;

    auto exchange = fetchEcosData(ecos_key, "731Y004", "0000001/0000100", start_date, end_date);
    cout << "3. 원-달러 환율: " << exchange.size() << " months fetched." << endl;

    auto exports  = fetchEcosData(ecos_key, "901Y118", "T002", start_date, end_date);
    auto imports  = fetchEcosData(ecos_key, "901Y118", "T004", start_date, end_date);
    cout << "4. 수출입 총괄: " << exports.size() << " months fetched." << endl;

    auto loans    = fetchEcosData(ecos_key, "151Y005", "11110A0", start_date, end_date);
    cout << "5. 가계대출: " << loans.size() << " months fetched." << endl;

    size_t min_len = rates.size();
    min_len = min(min_len, cpis.size());
    min_len = min(min_len, exchange.size());
    min_len = min(min_len, exports.size());
    min_len = min(min_len, imports.size());
    min_len = min(min_len, loans.size());

    if (min_len == 0) {
        cerr << "[Error] 한국 ECOS 데이터를 가져오는데 실패했습니다. 키나 인터넷 연결을 확인하세요." << endl;
        return;
    }

    // (2) 미국 FRED (선택적)
    vector<pair<string,string>> fedfunds;
    vector<pair<string,string>> us_cpi;
    if (!fred_key.empty()) {
        fedfunds = fetchFredSeries(fred_key, "FEDFUNDS", fred_start, fred_end);
        us_cpi   = fetchFredSeries(fred_key, "CPIAUCSL", fred_start, fred_end);
        cout << "6. 미국 기준금리(FEDFUNDS): " << fedfunds.size() << " obs fetched." << endl;
        cout << "7. 미국 CPI(CPIAUCSL): " << us_cpi.size() << " obs fetched." << endl;
    }

    // (3) World Bank 글로벌/미국 연간 지표
    auto wld_gdp = fetchWorldBankSeries("WLD", "NY.GDP.MKTP.KD.ZG", wb_start_year, wb_end_year);
    auto wld_cpi = fetchWorldBankSeries("WLD", "FP.CPI.TOTL.ZG",    wb_start_year, wb_end_year);
    auto usa_gdp = fetchWorldBankSeries("USA", "NY.GDP.MKTP.KD.ZG", wb_start_year, wb_end_year);
    auto usa_cpi = fetchWorldBankSeries("USA", "FP.CPI.TOTL.ZG",    wb_start_year, wb_end_year);

    cout << "8. World GDP 성장률: " << wld_gdp.size() << " yrs fetched." << endl;
    cout << "9. World CPI 인플레: " << wld_cpi.size() << " yrs fetched." << endl;
    cout << "10. USA GDP 성장률: " << usa_gdp.size() << " yrs fetched." << endl;
    cout << "11. USA CPI 인플레: " << usa_cpi.size() << " yrs fetched." << endl;

    // ===== CSV 프롬프트 구성 =====
    string csv_data;

    // 한국 월별 데이터
    {
        stringstream ss;
        ss << "### Korea monthly macro (ECOS)\n";
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
        csv_data += ss.str();
    }

    // 미국 월별 데이터(FRED) – 존재할 때만 추가
    if (!fedfunds.empty() && !us_cpi.empty()) {
        csv_data += "\n\n### US monthly macro (FRED)\n";
        csv_data += "Date, FedFundsRate(%), US_CPI_Index\n";
        size_t len = min(fedfunds.size(), us_cpi.size());
        for (size_t i = 0; i < len; ++i) {
            csv_data += fedfunds[i].first + ", " +
                        fedfunds[i].second + ", " +
                        us_cpi[i].second + "\n";
        }
    }

    // World & US 연간 데이터 (World Bank)
    {
        csv_data += "\n\n### World & US annual macro (World Bank)\n";
        csv_data += "Year, WLD_GDP_Growth(%), WLD_Inflation(%), USA_GDP_Growth(%), USA_Inflation(%)\n";

        size_t wb_len = wld_gdp.size();
        wb_len = min(wb_len, wld_cpi.size());
        wb_len = min(wb_len, usa_gdp.size());
        wb_len = min(wb_len, usa_cpi.size());

        for (size_t i = 0; i < wb_len; ++i) {
            csv_data += wld_gdp[i].first + ", " +
                        wld_gdp[i].second + ", " +
                        wld_cpi[i].second + ", " +
                        usa_gdp[i].second + ", " +
                        usa_cpi[i].second + "\n";
        }
    }

    // ===== Gemini 호출 및 S3 업로드 =====
    cout << "\n=== Sending Data to Gemini 3 (Grounded) ===" << endl;

    const char* bucket_name = "quartz-bucket";
    S3Uploader uploader("ap-northeast-2");

    cout << "\nGenerating & Uploading Reports..." << endl;

    string timestamp = getCurrentTimestamp();
    cout << "   Timestamp: " << timestamp << endl;

    // S3 폴더 경로
    const string s3_folder = "macro-analysis/";

    // 긍정 보고서
    cout << "   - Generating Positive Report..." << endl;
    string pos_report = generateGeminiReport(csv_data, "positive", gemini_key);
    if (!pos_report.empty()) {
        string fname = s3_folder + "Report_Positive_" + timestamp + ".md";
        if (uploader.uploadFile(bucket_name, fname, pos_report)) {
            cout << "   [Success] Uploaded: " << fname << endl;
        }

        cout << "   - Generating Positive Summary..." << endl;
        string pos_summary = summarizeReport(pos_report, "positive", gemini_key);
        if (!pos_summary.empty()) {
            string fname_short = s3_folder + "Report_Positive_" + timestamp + "_short.md";
            if (uploader.uploadFile(bucket_name, fname_short, pos_summary)) {
                cout << "   [Success] Uploaded: " << fname_short << endl;
            }
        }
    }

    // 부정 보고서
    cout << "   - Generating Negative Report..." << endl;
    string neg_report = generateGeminiReport(csv_data, "negative", gemini_key);
    if (!neg_report.empty()) {
        string fname = s3_folder + "Report_Negative_" + timestamp + ".md";
        if (uploader.uploadFile(bucket_name, fname, neg_report)) {
            cout << "   [Success] Uploaded: " << fname << endl;
        }

        cout << "   - Generating Negative Summary..." << endl;
        string neg_summary = summarizeReport(neg_report, "negative", gemini_key);
        if (!neg_summary.empty()) {
            string fname_short = s3_folder + "Report_Negative_" + timestamp + "_short.md";
            if (uploader.uploadFile(bucket_name, fname_short, neg_summary)) {
                cout << "   [Success] Uploaded: " << fname_short << endl;
            }
        }
    }
}

int main() {
    cout << "프로그램 시작" << endl;
    run_analysis();
    cout << "프로그램 종료" << endl;
    return 0;
}
