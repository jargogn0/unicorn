// STOCKHOLM — engine-independent simulation core.
// Minimal JSON value, parser and writer. No exceptions, no RTTI, so it compiles
// unchanged inside Unreal Engine modules (which disable both) and in the
// standalone CMake test build.
#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace stockholm::sim {

class JsonValue {
public:
    enum class Type : uint8_t { Null, Bool, Number, String, Array, Object };
    using ArrayType = std::vector<JsonValue>;
    using ObjectType = std::map<std::string, JsonValue>;

    JsonValue() = default;
    JsonValue(std::nullptr_t) {}
    JsonValue(bool b) : type_(Type::Bool), bool_(b) {}
    JsonValue(int v) : type_(Type::Number), number_(static_cast<double>(v)) {}
    JsonValue(int64_t v) : type_(Type::Number), number_(static_cast<double>(v)) {}
    JsonValue(double v) : type_(Type::Number), number_(v) {}
    JsonValue(const char* s) : type_(Type::String), string_(s ? s : "") {}
    JsonValue(std::string s) : type_(Type::String), string_(std::move(s)) {}
    JsonValue(ArrayType a) : type_(Type::Array), array_(std::move(a)) {}
    JsonValue(ObjectType o) : type_(Type::Object), object_(std::move(o)) {}

    static JsonValue MakeArray() { return JsonValue(ArrayType{}); }
    static JsonValue MakeObject() { return JsonValue(ObjectType{}); }

    // Parses text. On failure returns Null and writes a message to outError
    // (if provided) including the byte offset of the problem.
    static JsonValue Parse(const std::string& text, std::string* outError = nullptr);

    // Serialises. indent < 0 produces compact output.
    std::string Dump(int indent = -1) const;

    Type GetType() const { return type_; }
    bool IsNull() const { return type_ == Type::Null; }
    bool IsBool() const { return type_ == Type::Bool; }
    bool IsNumber() const { return type_ == Type::Number; }
    bool IsString() const { return type_ == Type::String; }
    bool IsArray() const { return type_ == Type::Array; }
    bool IsObject() const { return type_ == Type::Object; }

    bool AsBool(bool fallback = false) const { return type_ == Type::Bool ? bool_ : fallback; }
    double AsNumber(double fallback = 0.0) const { return type_ == Type::Number ? number_ : fallback; }
    int AsInt(int fallback = 0) const { return type_ == Type::Number ? static_cast<int>(number_) : fallback; }
    const std::string& AsString() const;
    std::string AsString(const std::string& fallback) const { return type_ == Type::String ? string_ : fallback; }

    // Object access. Returns a shared static Null for missing keys / wrong type.
    const JsonValue& operator[](const std::string& key) const;
    bool Has(const std::string& key) const;
    JsonValue& Set(const std::string& key, JsonValue value);
    const ObjectType& Items() const;

    // Array access.
    const JsonValue& operator[](size_t index) const;
    size_t Size() const;
    JsonValue& Push(JsonValue value);
    const ArrayType& Elements() const;

private:
    void DumpTo(std::string& out, int indent, int depth) const;

    Type type_ = Type::Null;
    bool bool_ = false;
    double number_ = 0.0;
    std::string string_;
    ArrayType array_;
    ObjectType object_;
};

// Convenience helpers.
std::string ReadTextFile(const std::string& path, bool* ok = nullptr);
bool WriteTextFile(const std::string& path, const std::string& contents);

} // namespace stockholm::sim
