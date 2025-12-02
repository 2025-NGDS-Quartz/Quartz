/*****************************************************************************
 *	코스닥 종목 코드 파일 구조
 ****************************************************************************/
/*
1. SZ_SHRNCODE

의미: “Short Code = 단축코드”
내용: 우리가 보통 보는 6자리 숫자 종목코드를 담는 필드
예: 삼성전자 → 005930
KRX/증권사 공통으로 쓰는 숫자 코드라,
실제로 API 쓸 때는 이 값을 티커(symbol) 쓰게 되는 경우가 많아요.
(한국거래소 전종목 기본정보에도 “단축코드, 표준코드, 한글종목명 …” 식으로 같이 나오죠. 
KRX 데이터 시스템
)

2. SZ_STNDCODE
의미: “Standard Code = 표준코드”
내용: 유가증권 표준코드(KR코드) 같은, 예탁결제원/거래소 쪽에서 쓰는
12자리 표준 종목코드를 담는 필드라고 보면 됩니다.
형식 예: KR7005930003 처럼 앞에 KR로 시작하는 코드
세법/공시/정산 쪽 문서들 보면 “표준코드(단축코드가 아닌 전체코드)”라고 부르는 바로 그 값
일반 매매/시세 조회에서는 단축코드만으로 충분하고,
표준코드는 타 시스템 연계나 정산/보고용으로 주로 필요합니다.

3. SZ_KORNAME
의미: “Korean Name = 한글 종목명”
내용: 종목의 풀네임(한글 이름) 을 담는 문자열 필드
예: 삼성전자, NAVER, 카카오 같은 이름
UI에 뿌릴 때, 로그 찍을 때 등 사람이 읽을 이름으로 쓰는 값이에요.
*/

typedef struct
{
    char    mksc_shrn_iscd[SZ_SHRNCODE];        /* 단축코드                                     */
    char    stnd_iscd[SZ_STNDCODE];             /* 표준코드                                     */
    char    hts_kor_isnm[SZ_KORNAME];           /* 한글종목명                                   */
    char    scrt_grp_cls_code[2];               /* 증권그룹구분코드                             */
                                                /* ST:주권 MF:증권투자회사 RT:부동산투자회사    */
                                                /* SC:선박투자회사 IF:사회간접자본투융자회사    */
                                                /* DR:주식예탁증서 EW:ELW EF:ETF                */
                                                /* SW:신주인수권증권 SR:신주인수권증서          */
                                                /* BC:수익증권 FE:해외ETF FS:외국주권           */
    char    avls_scal_cls_code[1];              /* 시가총액 규모 구분 코드 유가                 */
                                                /* 0:제외 1:KOSDAQ100 2:KOSDAQmid300 3:KOSDAQsmall) */
    char    bstp_larg_div_code[4];              /* 지수업종 대분류 코드                         */
    char    bstp_medm_div_code[4];              /* 지수 업종 중분류 코드                        */
    char    bstp_smal_div_code[4];              /* 지수업종 소분류 코드                         */
    char    vntr_issu_yn[1];                    /* 벤처기업 여부 (Y/N)               		 */
    char    low_current_yn[1];               	/* 저유동성종목 여부 				*/
    char    krx_issu_yn[1];                     /* KRX 종목 여부                               */
    char    etp_prod_cls_code[1];            	/* ETP 상품구분코드				  */
						/* 0:해당없음 1:투자회사형 2:수익증권형	    */
						/* 3:ETN 4:손실제한ETN			    */
    char    krx100_issu_yn[1];                  /* KRX100 종목 여부 (Y/N)                       */
    char    krx_car_yn[1];                      /* KRX 자동차 여부                              */
    char    krx_smcn_yn[1];                     /* KRX 반도체 여부                              */
    char    krx_bio_yn[1];                      /* KRX 바이오 여부                              */
    char    krx_bank_yn[1];                     /* KRX 은행 여부                                */
    char    etpr_undt_objt_co_yn[1];            /* 기업인수목적회사여부 				*/
    char    krx_enrg_chms_yn[1];                /* KRX 에너지 화학 여부                         */
    char    krx_stel_yn[1];                     /* KRX 철강 여부                                */
    char    short_over_cls_code[1];             /* 단기과열종목구분코드 0:해당없음              */
                                                /* 1:지정예고 2:지정 3:지정연장(해제연기)       */
    char    krx_medi_cmnc_yn[1];                /* KRX 미디어 통신 여부                         */
    char    krx_cnst_yn[1];                     /* KRX 건설 여부                                */
    char    invt_alrm_yn[1];                    /* (코스닥)투자주의환기종목여부                 */
    char    krx_scrt_yn [1];                    /* KRX 증권 구분                                */
    char    krx_ship_yn [1];                    /* KRX 선박 구분                                */
    char    krx_insu_yn[1];                     /* KRX섹터지수 보험여부                         */
    char    krx_trnp_yn[1];                     /* KRX섹터지수 운송여부                         */
    char    ksq150_nmix_yn[1];                  /* KOSDAQ150지수여부 (Y,N)                     */
    char    stck_sdpr[9];                       /* 주식 기준가                                  */
    char    frml_mrkt_deal_qty_unit[5];         /* 정규 시장 매매 수량 단위                     */
    char    ovtm_mrkt_deal_qty_unit[5];         /* 시간외 시장 매매 수량 단위                   */
    char    trht_yn[1];                         /* 거래정지 여부                                */
    char    sltr_yn[1];                         /* 정리매매 여부                                */
    char    mang_issu_yn[1];                    /* 관리 종목 여부                               */
    char    mrkt_alrm_cls_code[2];              /* 시장 경고 구분 코드 (00:해당없음 01:투자주의 */
                                                /* 02:투자경고 03:투자위험)                     */
    char    mrkt_alrm_risk_adnt_yn[1];          /* 시장 경고위험 예고 여부                      */
    char    insn_pbnt_yn[1];                    /* 불성실 공시 여부                             */
    char    byps_lstn_yn[1];                    /* 우회 상장 여부                               */
    char    flng_cls_code[2];                   /* 락구분 코드 (00:해당사항없음 01:권리락       */
                                                /* 02:배당락 03:분배락 04:권배락 05:중간배당락  */
                                                /* 06:권리중간배당락 99:기타                    */
                                                /* SW,SR,EW는 미해당(SPACE)                   */
    char    fcam_mod_cls_code[2];               /* 액면가 변경 구분 코드 (00:해당없음           */
                                                /* 01:액면분할 02:액면병합 99:기타              */
    char    icic_cls_code[2];                   /* 증자 구분 코드 (00:해당없음 01:유상증자      */
                                                /* 02:무상증자 03:유무상증자 99:기타)           */
    char    marg_rate[3];                       /* 증거금 비율                                  */
    char    crdt_able[1];                       /* 신용주문 가능 여부                           */
    char    crdt_days[3];                       /* 신용기간                                     */
    char    prdy_vol[12];                       /* 전일 거래량                                  */
    char    stck_fcam[12];                      /* 주식 액면가                                  */
    char    stck_lstn_date[8];                  /* 주식 상장 일자                               */
    char    lstn_stcn[15];                      /* 상장 주수(천)                                */
    char    cpfn[21];                           /* 자본금                                       */
    char    stac_month[2];                      /* 결산 월                                      */
    char    po_prc[7];                          /* 공모 가격                                    */
    char    prst_cls_code[1];                   /* 우선주 구분 코드 (0:해당없음(보통주)         */
                                                /* 1:구형우선주 2:신형우선주                    */
    char    ssts_hot_yn[1];                     /* 공매도과열종목여부  				*/
    char    stange_runup_yn[1];                 /* 이상급등종목여부 				*/
    char    krx300_issu_yn[1];                  /* KRX300 종목 여부 (Y/N)                       */
    char    sale_account[9];                    /* 매출액                                       */
    char    bsop_prfi[9];                       /* 영업이익                                     */
    char    op_prfi[9];                         /* 경상이익                                     */
    char    thtr_ntin[5];                       /* 당기순이익                                   */
    char    roe[9];                             /* ROE(자기자본이익률)                          */
    char    base_date[8];                       /* 기준년월                                     */
    char    prdy_avls_scal[9];                  /* 전일기준 시가총액 (억)                       */
    char    grp_code[3];			/* 그룹사 코드                                  */
    char    co_crdt_limt_over_yn[1];            /* 회사신용한도초과여부                         */
    char    secu_lend_able_yn[1];               /* 담보대출가능여부                             */
    char    stln_able_yn[1];                    /* 대주가능여부                                 */
}	ST_KSQ_CODE;