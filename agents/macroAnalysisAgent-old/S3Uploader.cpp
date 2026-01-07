#include "S3Uploader.h"
#include <aws/core/Aws.h>
#include <aws/s3/S3Client.h>
#include <aws/s3/model/PutObjectRequest.h>
#include <iostream>
#include <sstream>

S3Uploader::S3Uploader(const std::string& region) {
    // AWS API 초기화
    auto opts = new Aws::SDKOptions;
    Aws::InitAPI(*opts);
    this->options = opts;
}

S3Uploader::~S3Uploader() {
    // AWS API 종료
    if (this->options) {
        Aws::SDKOptions* opts = static_cast<Aws::SDKOptions*>(this->options);
        Aws::ShutdownAPI(*opts);
        delete opts;
    }
}

bool S3Uploader::uploadFile(const std::string& bucketName, const std::string& key, const std::string& content) {
    // AWS 클라이언트 생성 및 PutObjectRequest 실행
    Aws::Client::ClientConfiguration clientConfig;
    clientConfig.region = "ap-northeast-2";
    Aws::S3::S3Client s3_client(clientConfig);

    Aws::S3::Model::PutObjectRequest request;
    request.SetBucket(bucketName.c_str());
    request.SetKey(key.c_str());

    // 문자열 데이터 -> 스트림 변환 후 body에 담기
    const std::shared_ptr<Aws::IOStream> input_data =
        Aws::MakeShared<Aws::StringStream>("PutObjectInputStream");
    *input_data << content;
    request.SetBody(input_data);

    // 전송
    auto outcome = s3_client.PutObject(request);

    // 결과 확인
    if (outcome.IsSuccess()) {
        std::cout << "[S3] Upload Success: " << key << std::endl;
        return true;
    }
    else {
        std::cerr << "[S3] Upload Failed: "
            << outcome.GetError().GetMessage() << std::endl;
        return false;
    }
}