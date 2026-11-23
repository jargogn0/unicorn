#include "Sim/Json.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>

namespace stockholm::sim {

namespace json_detail {

const JsonValue& NullValue() {
    static const JsonValue kNull;
    return kNull;
}
const std::string& EmptyString() {
    static const std::string kEmpty;
    return kEmpty;
}
const JsonValue::ArrayType& EmptyArray() {
    static const JsonValue::ArrayType kEmpty;
    return kEmpty;
}
const JsonValue::ObjectType& EmptyObject() {
    static const JsonValue::ObjectType kEmpty;
    return kEmpty;
}

class Parser {
public:
    explicit Parser(const std::string& text) : s_(text) {}

    bool ParseDocument(JsonValue& out) {
        SkipWs();
        if (!ParseValue(out, 0)) return false;
        SkipWs();
        if (pos_ != s_.size()) return Fail("trailing characters after JSON document");
        return true;
    }

    std::string error;

private:
    static constexpr int kMaxDepth = 256;

    bool Fail(const char* msg) {
        if (error.empty()) {
            char buf[64];
            std::snprintf(buf, sizeof(buf), " (at byte %zu)", pos_);
            error = std::string(msg) + buf;
        }
        return false;
    }

    void SkipWs() {
        while (pos_ < s_.size()) {
            const char c = s_[pos_];
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
                ++pos_;
            } else if (c == '/' && pos_ + 1 < s_.size() && s_[pos_ + 1] == '/') {
                // Tolerate line comments in hand-authored data files.
                while (pos_ < s_.size() && s_[pos_] != '\n') ++pos_;
            } else {
                break;
            }
        }
    }

    bool Match(const char* lit) {
        const size_t n = std::strlen(lit);
        if (s_.compare(pos_, n, lit) == 0) {
            pos_ += n;
            return true;
        }
        return false;
    }

    bool ParseValue(JsonValue& out, int depth) {
        if (depth > kMaxDepth) return Fail("nesting too deep");
        if (pos_ >= s_.size()) return Fail("unexpected end of input");
        const char c = s_[pos_];
        if (c == '{') return ParseObject(out, depth);
        if (c == '[') return ParseArray(out, depth);
        if (c == '"') {
            std::string str;
            if (!ParseString(str)) return false;
            out = JsonValue(std::move(str));
            return true;
        }
        if (Match("true")) { out = JsonValue(true); return true; }
        if (Match("false")) { out = JsonValue(false); return true; }
        if (Match("null")) { out = JsonValue(); return true; }
        if (c == '-' || (c >= '0' && c <= '9')) return ParseNumber(out);
        return Fail("unexpected character");
    }

    bool ParseNumber(JsonValue& out) {
        const char* begin = s_.c_str() + pos_;
        char* end = nullptr;
        const double v = std::strtod(begin, &end);
        if (end == begin) return Fail("invalid number");
        pos_ += static_cast<size_t>(end - begin);
        out = JsonValue(v);
        return true;
    }

    static void AppendUtf8(std::string& out, uint32_t cp) {
        if (cp < 0x80) {
            out.push_back(static_cast<char>(cp));
        } else if (cp < 0x800) {
            out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
            out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
        } else if (cp < 0x10000) {
            out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
            out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
        } else {
            out.push_back(static_cast<char>(0xF0 | (cp >> 18)));
            out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
            out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
        }
    }

    bool ParseHex4(uint32_t& out) {
        if (pos_ + 4 > s_.size()) return Fail("truncated unicode escape");
        out = 0;
        for (int i = 0; i < 4; ++i) {
            const char h = s_[pos_++];
            out <<= 4;
            if (h >= '0' && h <= '9') out |= static_cast<uint32_t>(h - '0');
            else if (h >= 'a' && h <= 'f') out |= static_cast<uint32_t>(h - 'a' + 10);
            else if (h >= 'A' && h <= 'F') out |= static_cast<uint32_t>(h - 'A' + 10);
            else return Fail("invalid unicode escape");
        }
        return true;
    }

    bool ParseString(std::string& out) {
        ++pos_; // opening quote
        while (pos_ < s_.size()) {
            const char c = s_[pos_++];
            if (c == '"') return true;
            if (c == '\\') {
                if (pos_ >= s_.size()) return Fail("truncated escape");
                const char e = s_[pos_++];
                switch (e) {
                    case '"': out.push_back('"'); break;
                    case '\\': out.push_back('\\'); break;
                    case '/': out.push_back('/'); break;
                    case 'b': out.push_back('\b'); break;
                    case 'f': out.push_back('\f'); break;
                    case 'n': out.push_back('\n'); break;
                    case 'r': out.push_back('\r'); break;
                    case 't': out.push_back('\t'); break;
                    case 'u': {
                        uint32_t cp = 0;
                        if (!ParseHex4(cp)) return false;
                        if (cp >= 0xD800 && cp <= 0xDBFF) {
                            if (!(Match("\\u"))) return Fail("unpaired surrogate");
                            uint32_t lo = 0;
                            if (!ParseHex4(lo)) return false;
                            if (lo < 0xDC00 || lo > 0xDFFF) return Fail("invalid low surrogate");
                            cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                        }
                        AppendUtf8(out, cp);
                        break;
                    }
                    default: return Fail("invalid escape character");
                }
            } else {
                out.push_back(c);
            }
        }
        return Fail("unterminated string");
    }

    bool ParseArray(JsonValue& out, int depth) {
        ++pos_;
        out = JsonValue::MakeArray();
        SkipWs();
        if (pos_ < s_.size() && s_[pos_] == ']') { ++pos_; return true; }
        while (true) {
            SkipWs();
            JsonValue element;
            if (!ParseValue(element, depth + 1)) return false;
            out.Push(std::move(element));
            SkipWs();
            if (pos_ >= s_.size()) return Fail("unterminated array");
            if (s_[pos_] == ',') { ++pos_; continue; }
            if (s_[pos_] == ']') { ++pos_; return true; }
            return Fail("expected ',' or ']'");
        }
    }

    bool ParseObject(JsonValue& out, int depth) {
        ++pos_;
        out = JsonValue::MakeObject();
        SkipWs();
        if (pos_ < s_.size() && s_[pos_] == '}') { ++pos_; return true; }
        while (true) {
            SkipWs();
            if (pos_ >= s_.size() || s_[pos_] != '"') return Fail("expected object key");
            std::string key;
            if (!ParseString(key)) return false;
            SkipWs();
            if (pos_ >= s_.size() || s_[pos_] != ':') return Fail("expected ':'");
            ++pos_;
            SkipWs();
            JsonValue value;
            if (!ParseValue(value, depth + 1)) return false;
            out.Set(key, std::move(value));
            SkipWs();
            if (pos_ >= s_.size()) return Fail("unterminated object");
            if (s_[pos_] == ',') { ++pos_; continue; }
            if (s_[pos_] == '}') { ++pos_; return true; }
            return Fail("expected ',' or '}'");
        }
    }

    const std::string& s_;
    size_t pos_ = 0;
};

void EscapeString(std::string& out, const std::string& s) {
    out.push_back('"');
    for (const char ch : s) {
        const unsigned char c = static_cast<unsigned char>(ch);
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if (c < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", c);
                    out += buf;
                } else {
                    out.push_back(ch);
                }
        }
    }
    out.push_back('"');
}

void Newline(std::string& out, int indent, int depth) {
    if (indent < 0) return;
    out.push_back('\n');
    out.append(static_cast<size_t>(indent * depth), ' ');
}

} // namespace json_detail

JsonValue JsonValue::Parse(const std::string& text, std::string* outError) {
    json_detail::Parser parser(text);
    JsonValue result;
    if (!parser.ParseDocument(result)) {
        if (outError) *outError = parser.error;
        return JsonValue();
    }
    if (outError) outError->clear();
    return result;
}

const std::string& JsonValue::AsString() const {
    return type_ == Type::String ? string_ : json_detail::EmptyString();
}

const JsonValue& JsonValue::operator[](const std::string& key) const {
    if (type_ != Type::Object) return json_detail::NullValue();
    const auto it = object_.find(key);
    return it == object_.end() ? json_detail::NullValue() : it->second;
}

bool JsonValue::Has(const std::string& key) const {
    return type_ == Type::Object && object_.count(key) > 0;
}

JsonValue& JsonValue::Set(const std::string& key, JsonValue value) {
    if (type_ != Type::Object) {
        *this = MakeObject();
    }
    JsonValue& slot = object_[key];
    slot = std::move(value);
    return slot;
}

const JsonValue::ObjectType& JsonValue::Items() const {
    return type_ == Type::Object ? object_ : json_detail::EmptyObject();
}

const JsonValue& JsonValue::operator[](size_t index) const {
    if (type_ != Type::Array || index >= array_.size()) return json_detail::NullValue();
    return array_[index];
}

size_t JsonValue::Size() const {
    if (type_ == Type::Array) return array_.size();
    if (type_ == Type::Object) return object_.size();
    return 0;
}

JsonValue& JsonValue::Push(JsonValue value) {
    if (type_ != Type::Array) {
        *this = MakeArray();
    }
    array_.push_back(std::move(value));
    return array_.back();
}

const JsonValue::ArrayType& JsonValue::Elements() const {
    return type_ == Type::Array ? array_ : json_detail::EmptyArray();
}

std::string JsonValue::Dump(int indent) const {
    std::string out;
    DumpTo(out, indent, 0);
    return out;
}

void JsonValue::DumpTo(std::string& out, int indent, int depth) const {
    switch (type_) {
        case Type::Null: out += "null"; break;
        case Type::Bool: out += bool_ ? "true" : "false"; break;
        case Type::Number: {
            if (!std::isfinite(number_)) {
                out += "null";
            } else if (std::fabs(number_) < 1e15 && number_ == std::floor(number_)) {
                char buf[32];
                std::snprintf(buf, sizeof(buf), "%lld", static_cast<long long>(number_));
                out += buf;
            } else {
                char buf[40];
                std::snprintf(buf, sizeof(buf), "%.17g", number_);
                out += buf;
            }
            break;
        }
        case Type::String: json_detail::EscapeString(out, string_); break;
        case Type::Array: {
            out.push_back('[');
            bool first = true;
            for (const JsonValue& v : array_) {
                if (!first) out.push_back(',');
                first = false;
                json_detail::Newline(out, indent, depth + 1);
                v.DumpTo(out, indent, depth + 1);
            }
            if (!array_.empty()) json_detail::Newline(out, indent, depth);
            out.push_back(']');
            break;
        }
        case Type::Object: {
            out.push_back('{');
            bool first = true;
            for (const auto& kv : object_) {
                if (!first) out.push_back(',');
                first = false;
                json_detail::Newline(out, indent, depth + 1);
                json_detail::EscapeString(out, kv.first);
                out += indent >= 0 ? ": " : ":";
                kv.second.DumpTo(out, indent, depth + 1);
            }
            if (!object_.empty()) json_detail::Newline(out, indent, depth);
            out.push_back('}');
            break;
        }
    }
}

std::string ReadTextFile(const std::string& path, bool* ok) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        if (ok) *ok = false;
        return {};
    }
    std::ostringstream ss;
    ss << in.rdbuf();
    if (ok) *ok = true;
    return ss.str();
}

bool WriteTextFile(const std::string& path, const std::string& contents) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) return false;
    out << contents;
    return static_cast<bool>(out);
}

} // namespace stockholm::sim
