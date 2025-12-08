#pragma once
#include <string>

class S3Uploader {
public:
    S3Uploader(const std::string& region = "ap-northeast-2");
    ~S3Uploader();

    bool uploadFile(const std::string& bucketName, const std::string& key, const std::string& content);

private:
    void* options; 
};