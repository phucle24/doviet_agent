from copy import deepcopy


SERIES_ROTATION = [
    "do_tuc_ngu",
    "do_ca_dao",
    "duoi_hinh_bat_chu",
    "do_meo_dan_gian",
]

SERIES_META = {
    "do_tuc_ngu": {
        "label": "ĐỐ TỤC NGỮ",
        "hashtag": "#dotucngu",
        "default_prompt": "Nhìn hình đoán câu tục ngữ quen thuộc.",
        "default_answer_prefix": "Đáp án tục ngữ",
    },
    "do_ca_dao": {
        "label": "ĐỐ CA DAO",
        "hashtag": "#docadao",
        "default_prompt": "Nhìn hình đoán câu ca dao quen thuộc.",
        "default_answer_prefix": "Đáp án ca dao",
    },
    "duoi_hinh_bat_chu": {
        "label": "ĐUỔI HÌNH BẮT CHỮ",
        "hashtag": "#duoihinhbatchu",
        "default_prompt": "Nhìn hình đoán cụm từ.",
        "default_answer_prefix": "Đáp án",
    },
    "do_meo_dan_gian": {
        "label": "ĐỐ MẸO DÂN GIAN",
        "hashtag": "#domeodangian",
        "default_prompt": "Câu đố mẹo dân gian.",
        "default_answer_prefix": "Đáp án",
    },
}

RIDDLE_TOPICS = {
    "do_tuc_ngu": [
        {
            "topic_key": "mot_cay_lam_chang_nen_non",
            "format": "Nhìn hình đoán tục ngữ",
            "title": "Một bức hình, một câu tục ngữ quen thuộc",
            "prompt_line": "Nhìn hình đoán câu tục ngữ quen thuộc.",
            "clue": "Câu này nói về sự đoàn kết.",
            "answer": "Một cây làm chẳng nên non, ba cây chụm lại nên hòn núi cao.",
            "answer_note": "Ý nói đoàn kết sẽ tạo nên sức mạnh lớn hơn từng cá nhân riêng lẻ.",
            "image_brief": "one small bamboo tree standing alone, next to three bamboo trees tied together forming a strong mountain-like shape, Vietnamese folk village background",
            "image_text": "ĐOÁN TỤC NGỮ\nGợi ý: Đoàn kết",
        },
        {
            "topic_key": "co_cong_mai_sat",
            "format": "Điền từ còn thiếu trong tục ngữ",
            "title": "Bạn còn nhớ câu tục ngữ này không?",
            "prompt_line": "Điền từ còn thiếu trong câu tục ngữ.",
            "clue": "Có công mài sắt, có ngày nên ...",
            "answer": "Có công mài sắt, có ngày nên kim.",
            "answer_note": "Câu này nhắc về sự kiên trì, bền bỉ.",
            "image_brief": "a person patiently grinding an iron bar into a needle, old Vietnamese courtyard, warm morning light",
            "image_text": "CÓ CÔNG MÀI SẮT\nCÓ NGÀY NÊN ...",
        },
        {
            "topic_key": "an_qua_nho_ke_trong_cay",
            "format": "Nhìn hình đoán tục ngữ",
            "title": "Nhìn hình đoán tục ngữ: 90% người đoán sai câu này",
            "prompt_line": "Nhìn hình đoán câu tục ngữ quen thuộc.",
            "clue": "Câu này nói về lòng biết ơn.",
            "answer": "Ăn quả nhớ kẻ trồng cây.",
            "answer_note": "Khi hưởng thành quả, cần nhớ công lao người tạo nên nó.",
            "image_brief": "ripe fruit in a hand, an elderly farmer planting a young tree in the background, Vietnamese countryside",
            "image_text": "ĐOÁN TỤC NGỮ\nGợi ý: Biết ơn",
        },
        {
            "topic_key": "gan_muc_thi_den",
            "format": "Chọn đáp án đúng",
            "title": "Một hình ảnh gợi ra câu tục ngữ rất quen",
            "prompt_line": "Nhìn hình và đoán câu tục ngữ.",
            "clue": "Câu này nói về ảnh hưởng của môi trường sống.",
            "answer": "Gần mực thì đen, gần đèn thì sáng.",
            "answer_note": "Môi trường và người xung quanh có thể ảnh hưởng mạnh đến tính cách, thói quen.",
            "image_brief": "black ink pot on one side and glowing oil lamp on the other side, a person standing between darkness and warm light, folk poster style",
            "image_text": "GẦN MỰC?\nGẦN ĐÈN?",
        },
        {
            "topic_key": "la_lanh_dum_la_rach",
            "format": "Tục ngữ bị che chữ",
            "title": "Một câu tục ngữ về tình thương người Việt",
            "prompt_line": "Đoán phần bị che trong câu tục ngữ.",
            "clue": "Lá lành đùm lá ...",
            "answer": "Lá lành đùm lá rách.",
            "answer_note": "Người có điều kiện hơn nên giúp đỡ người đang khó khăn.",
            "image_brief": "fresh green leaves gently wrapping a torn leaf, Vietnamese village texture, soft humane feeling",
            "image_text": "LÁ LÀNH ĐÙM LÁ ...",
        },
    ],
    "do_ca_dao": [
        {
            "topic_key": "con_oi_nho_lay_cau_nay",
            "format": "Điền câu tiếp theo",
            "title": "Điền tiếp câu ca dao này, bạn làm được không?",
            "prompt_line": "Điền tiếp câu ca dao quen thuộc.",
            "clue": "Con ơi nhớ lấy câu này...",
            "answer": "Con ơi nhớ lấy câu này, công cha nghĩa mẹ ơn thầy chớ quên.",
            "answer_note": "Câu ca dao nhắc về đạo hiếu và lòng biết ơn thầy cô.",
            "image_brief": "Vietnamese child studying beside parents and a teacher silhouette, warm traditional home, respectful mood",
            "image_text": "CON ƠI NHỚ LẤY CÂU NÀY...",
        },
        {
            "topic_key": "bau_oi_thuong_lay_bi_cung",
            "format": "Nhìn hình đoán câu ca dao",
            "title": "Nhìn hình đoán ca dao: câu này ai học rồi cũng nhớ",
            "prompt_line": "Nhìn hình đoán câu ca dao quen thuộc.",
            "clue": "Câu này nói về tình thương giữa người cùng một nước.",
            "answer": "Bầu ơi thương lấy bí cùng, tuy rằng khác giống nhưng chung một giàn.",
            "answer_note": "Ý nói con người nên yêu thương, đùm bọc nhau.",
            "image_brief": "gourd and squash growing together on the same vine trellis, Vietnamese garden, soft daylight",
            "image_text": "BẦU ƠI...\nGợi ý: Chung một giàn",
        },
        {
            "topic_key": "con_co_bay_la_bay_la",
            "format": "Ca dao bị che chữ",
            "title": "Một hình ảnh gợi nhớ cả tuổi thơ",
            "prompt_line": "Đoán câu ca dao qua hình ảnh.",
            "clue": "Có con cò bay qua cánh đồng.",
            "answer": "Con cò bay lả bay la, bay từ cửa phủ bay ra cánh đồng.",
            "answer_note": "Hình ảnh con cò gắn với đồng quê và tuổi thơ Việt Nam.",
            "image_brief": "white storks flying over golden rice fields, distant village gate, peaceful Vietnamese countryside",
            "image_text": "CON CÒ BAY ... BAY ...",
        },
        {
            "topic_key": "trong_dam_gi_dep_bang_sen",
            "format": "Điền câu tiếp theo",
            "title": "Câu ca dao này nhìn hình là nhớ ngay",
            "prompt_line": "Điền tiếp câu ca dao về hoa sen.",
            "clue": "Trong đầm gì đẹp bằng sen...",
            "answer": "Trong đầm gì đẹp bằng sen, lá xanh bông trắng lại chen nhị vàng.",
            "answer_note": "Câu ca dao ca ngợi vẻ đẹp thanh khiết của hoa sen.",
            "image_brief": "Vietnamese lotus pond with green leaves, white blossoms and yellow stamens, elegant traditional composition",
            "image_text": "TRONG ĐẦM GÌ ĐẸP BẰNG SEN...",
        },
        {
            "topic_key": "anh_di_anh_nho_que_nha",
            "format": "Đố ca dao về quê hương",
            "title": "Câu ca dao về quê nhà nhiều người thuộc lòng",
            "prompt_line": "Nhìn hình đoán câu ca dao về quê hương.",
            "clue": "Có canh rau muống, có cà dầm tương.",
            "answer": "Anh đi anh nhớ quê nhà, nhớ canh rau muống nhớ cà dầm tương.",
            "answer_note": "Câu ca dao gợi nỗi nhớ quê qua những món ăn bình dị.",
            "image_brief": "simple Vietnamese meal with water spinach soup and pickled eggplant, rustic village kitchen, nostalgic mood",
            "image_text": "ANH ĐI ANH NHỚ QUÊ NHÀ...",
        },
    ],
    "duoi_hinh_bat_chu": [
        {
            "topic_key": "mat_troi_chan_ly",
            "format": "2-4 hình ghép thành một cụm từ",
            "title": "Đuổi hình bắt chữ: nhìn dễ mà không dễ",
            "prompt_line": "Ghép các hình lại để đoán cụm từ.",
            "clue": "Mặt trời + chân + lý.",
            "answer": "Mặt trời chân lý.",
            "answer_note": "Đây là kiểu bắt chữ theo âm và nghĩa của từng hình.",
            "image_brief": "three clear rebus panels: bright sun, human foot, scales of justice or truth symbol, playful Vietnamese puzzle poster",
            "image_text": "ĐUỔI HÌNH BẮT CHỮ\n☀ + CHÂN + LÝ",
        },
        {
            "topic_key": "ca_chep_hoa_rong",
            "format": "Bắt chữ theo nghĩa",
            "title": "Ai đoán được trong 5 giây là quá đỉnh",
            "prompt_line": "Nhìn hình đoán thành ngữ/cụm từ.",
            "clue": "Một con cá đang vượt lên và biến hóa.",
            "answer": "Cá chép hóa rồng.",
            "answer_note": "Cụm từ thường nói về sự vươn lên, đổi đời.",
            "image_brief": "carp leaping through a golden gate and transforming into a dragon, Vietnamese folk art style, energetic",
            "image_text": "ĐOÁN CỤM TỪ\nCÁ + ?",
        },
        {
            "topic_key": "nuoc_mat_ca_sau",
            "format": "Đoán từ khóa qua icon",
            "title": "Câu này nhìn hình là lú luôn",
            "prompt_line": "Nhìn hình đoán cụm từ quen thuộc.",
            "clue": "Giọt nước mắt và một con cá sấu.",
            "answer": "Nước mắt cá sấu.",
            "answer_note": "Cụm từ chỉ sự giả vờ thương xót, không thật lòng.",
            "image_brief": "a crocodile with exaggerated tear drops, comic folk poster, clean rebus layout",
            "image_text": "💧 + CÁ SẤU = ?",
        },
        {
            "topic_key": "gao_nep_gao_te",
            "format": "Bắt chữ chủ đề đời sống",
            "title": "Cụm từ đời sống này bạn đoán ra không?",
            "prompt_line": "Nhìn hình đoán cụm từ quen thuộc.",
            "clue": "Hai loại gạo đặt cạnh nhau.",
            "answer": "Gạo nếp gạo tẻ.",
            "answer_note": "Đáp án dựa trực tiếp vào hình ảnh hai loại gạo.",
            "image_brief": "two labeled-looking but not text-labeled bowls of sticky rice grains and regular rice grains, Vietnamese kitchen, clean puzzle composition",
            "image_text": "GẠO ? + GẠO ?",
        },
        {
            "topic_key": "rau_nao_sau_ay",
            "format": "Bắt chữ theo âm",
            "title": "Nhìn kỹ mới thấy đáp án rất quen",
            "prompt_line": "Nhìn hình đoán câu nói quen thuộc.",
            "clue": "Rau + nào + sâu + ấy.",
            "answer": "Rau nào sâu ấy.",
            "answer_note": "Đây là kiểu đuổi hình bắt chữ theo âm từng phần.",
            "image_brief": "four rebus panels: leafy vegetables, question mark, small worm, matching pair symbol, playful Vietnamese puzzle poster",
            "image_text": "RAU + NÀO + SÂU + ẤY",
        },
    ],
    "do_meo_dan_gian": [
        {
            "topic_key": "cang_lay_cang_lon",
            "format": "Câu hỏi mẹo",
            "title": "Nghe đơn giản nhưng 80% trả lời sai",
            "prompt_line": "Câu đố mẹo dân gian.",
            "clue": "Cái gì càng lấy đi thì càng lớn?",
            "answer": "Cái hố.",
            "answer_note": "Càng đào/lấy đất đi thì cái hố càng lớn.",
            "image_brief": "a small hole in the ground becoming larger as soil is removed, simple rustic Vietnamese yard, playful mystery mood",
            "image_text": "CÀNG LẤY ĐI\nCÀNG LỚN?",
        },
        {
            "topic_key": "vua_bang_cai_vung",
            "format": "Câu đố vui dân gian",
            "title": "Đố vui dân gian: bạn mất bao lâu để nghĩ ra đáp án?",
            "prompt_line": "Đố vui dân gian.",
            "clue": "Vừa bằng cái vung, vùng xuống ao. Đào chẳng thấy, lấy chẳng được. Là gì?",
            "answer": "Mặt trăng.",
            "answer_note": "Mặt trăng in bóng xuống ao, nhìn thấy nhưng không lấy được.",
            "image_brief": "full moon reflected in a village pond, a round pot lid shape comparison, night Vietnamese countryside",
            "image_text": "VỪA BẰNG CÁI VUNG\nVÙNG XUỐNG AO",
        },
        {
            "topic_key": "khong_mieng_ma_keu",
            "format": "Câu đố nghe vậy mà không phải vậy",
            "title": "Trẻ con đoán đúng, người lớn suy nghĩ quá nhiều",
            "prompt_line": "Câu đố mẹo dân gian.",
            "clue": "Không miệng mà kêu, không chân mà chạy. Là gì?",
            "answer": "Cái trống.",
            "answer_note": "Trống không có miệng nhưng phát tiếng; tiếng trống vang đi như đang chạy.",
            "image_brief": "traditional Vietnamese drum with sound waves traveling through a village festival scene",
            "image_text": "KHÔNG MIỆNG MÀ KÊU\nKHÔNG CHÂN MÀ CHẠY",
        },
        {
            "topic_key": "di_dau_cung_doi_mu",
            "format": "Đố mẹo trẻ em",
            "title": "Câu này dễ mà không hề dễ",
            "prompt_line": "Câu đố mẹo dân gian.",
            "clue": "Cái gì đi đâu cũng đội mũ?",
            "answer": "Cây nấm.",
            "answer_note": "Phần mũ nấm nằm trên thân nấm nên nhìn như lúc nào cũng đội mũ.",
            "image_brief": "cute mushrooms with cap-like tops in a damp garden, Vietnamese folk illustration poster style",
            "image_text": "ĐI ĐÂU CŨNG ĐỘI MŨ?",
        },
        {
            "topic_key": "co_rang_khong_mieng",
            "format": "Đố logic nhẹ",
            "title": "Nghe vậy mà không phải vậy",
            "prompt_line": "Câu đố mẹo dân gian.",
            "clue": "Có răng mà không có miệng. Là gì?",
            "answer": "Cái lược.",
            "answer_note": "Răng lược là cách gọi các khe/chấu nhỏ của chiếc lược.",
            "image_brief": "traditional comb with many teeth on a wooden table, simple clean folk riddle poster",
            "image_text": "CÓ RĂNG\nKHÔNG CÓ MIỆNG?",
        },
    ],
}


def topic_pool_size() -> int:
    return sum(len(topics) for topics in RIDDLE_TOPICS.values())


def static_topic_count_for_series(series_key: str) -> int:
    return len(RIDDLE_TOPICS[series_key])


def annotate_topic(topic: dict, series_key: str, series_number: int) -> dict:
    meta = SERIES_META[series_key]

    topic["topic_type"] = "vietnamese_riddle"
    topic["series_key"] = series_key
    topic["series_label"] = meta["label"]
    topic["series_hashtag"] = meta["hashtag"]
    topic["series_number"] = series_number
    topic["default_prompt"] = meta["default_prompt"]
    topic["default_answer_prefix"] = meta["default_answer_prefix"]
    return topic


def get_topic_by_index(index: int) -> dict:
    series_key = SERIES_ROTATION[index % len(SERIES_ROTATION)]
    series_topics = RIDDLE_TOPICS[series_key]
    series_index = index // len(SERIES_ROTATION)
    topic = deepcopy(series_topics[series_index % len(series_topics)])
    return annotate_topic(topic, series_key, series_index + 1)


def get_static_topic(series_key: str, topic_index: int, series_number: int) -> dict:
    topic = deepcopy(RIDDLE_TOPICS[series_key][topic_index])
    return annotate_topic(topic, series_key, series_number)


def series_for_global_index(index: int) -> tuple[str, int]:
    series_key = SERIES_ROTATION[index % len(SERIES_ROTATION)]
    return series_key, (index // len(SERIES_ROTATION)) + 1
