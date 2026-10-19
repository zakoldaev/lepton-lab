// Lepton 3.x raw VoSPI bridge. Uses Linux spidev, mode 3, 20 MHz,
// matching the working GroupGets viewer's interface. No camera settings changed.
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#ifdef __linux__
#include <cerrno>
#include <fcntl.h>
#include <linux/spi/spidev.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <unistd.h>
#endif

using Frame = std::array<uint16_t, 160 * 120>;
using Packet = std::array<uint8_t, 164>;
using Clock = std::chrono::steady_clock;

// Emit only complete, ordered groups of four 60-packet segments.
// Telemetry must be off, as in the existing raspberrypi_video viewer.
class Assembler {
    int packet_ = 0, segment_ = 0, expected_ = 1;
    std::array<Packet, 60> segmentData_{};
    Frame frame_{};
    Clock::time_point started_ = Clock::now();
public:
    void reset() { packet_ = 0; segment_ = 0; expected_ = 1; }
    bool push(const Packet& p, Frame& output) {
        if (expected_ != 1 && Clock::now() - started_ > std::chrono::milliseconds(250)) reset();
        if ((p[0] & 0x0f) == 0x0f) {
            if (packet_ != 0) reset();
            return false;
        }
        int number = ((p[0] & 0x0f) << 8) | p[1];
        if (number != packet_) {
            reset();
            if (number != 0) return false;
        }
        if (number >= 60) { reset(); return false; }
        segmentData_[number] = p;
        if (number == 20) {
            segment_ = (p[0] >> 4) & 7;
            if (segment_ < 1 || segment_ > 4) { reset(); return false; }
        }
        if (++packet_ != 60) return false;
        packet_ = 0;
        if (segment_ == 1) { expected_ = 1; started_ = Clock::now(); }
        if (segment_ != expected_) { reset(); return false; }
        for (int n = 0; n < 60; ++n) {
            int row = (segment_ - 1) * 30 + n / 2;
            int x = (n % 2) * 80;
            for (int i = 0; i < 80; ++i) {
                const Packet& s = segmentData_[n];
                frame_[row * 160 + x + i] = (uint16_t(s[4 + 2*i]) << 8) | s[5 + 2*i];
            }
        }
        if (++expected_ == 5) { output = frame_; expected_ = 1; return true; }
        return false;
    }
};

void putLE(unsigned char* p, uint64_t value, int n) {
    for (int i = 0; i < n; ++i) p[i] = (value >> (8*i)) & 255;
}
void emitFrame(const Frame& frame, uint64_t sequence) {
    std::array<unsigned char, 32 + 160*120*2> bytes{};
    std::memcpy(bytes.data(), "LPT1", 4);
    putLE(bytes.data()+4, 160, 2); putLE(bytes.data()+6, 120, 2);
    putLE(bytes.data()+8, sequence, 8);
    auto mono = std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count();
    auto utc = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
    putLE(bytes.data()+16, mono, 8); putLE(bytes.data()+24, utc, 8);
    for (size_t i=0; i<frame.size(); ++i) putLE(bytes.data()+32+2*i, frame[i], 2);
    if (std::fwrite(bytes.data(), 1, bytes.size(), stdout) != bytes.size() || std::fflush(stdout))
        throw std::runtime_error("Viewer closed or output pipe failed");
}

Packet synthetic(int segment, int number) {
    Packet p{}; p[1] = number;
    if (number == 20) p[0] = segment << 4;
    for (int i=0; i<80; ++i) {
        uint16_t v = ((segment-1)*30 + number/2)*160 + (number%2)*80 + i;
        p[4+2*i] = v >> 8; p[5+2*i] = v & 255;
    }
    return p;
}
void selfTest() {
    Assembler a; Frame f{}; int emitted = 0;
    for (int s=1; s<=4; ++s) for(int p=0; p<60; ++p) emitted += a.push(synthetic(s,p), f);
    if (emitted != 1) throw std::runtime_error("Complete frame not emitted");
    for (size_t i=0; i<f.size(); ++i) if (f[i] != i) throw std::runtime_error("Pixel layout or endian mismatch");
    // Missing segment: never fill it with stale pixels from a previous frame.
    for (int s : {1,3,4}) for(int p=0; p<60; ++p)
        if (a.push(synthetic(s,p), f)) throw std::runtime_error("Incomplete frame accepted");
    // Missing packet: abandon the damaged segment.
    for(int p=0; p<60; ++p) if(p != 11)
        if(a.push(synthetic(1,p), f)) throw std::runtime_error("Damaged frame accepted");
    Packet discard{}; discard[0]=0x0f; a.push(discard,f);
    emitted=0;
    for(int s=1;s<=4;++s) for(int p=0;p<60;++p) emitted+=a.push(synthetic(s,p),f);
    if(emitted != 1) throw std::runtime_error("Failed to recover after damaged frame");
    std::cerr << "Packet assembly tests passed\n";
}

int main(int argc, char** argv) {
    try {
        std::string arg = argc>1 ? argv[1] : "/dev/spidev0.0";
        if(arg == "--self-test") { selfTest(); return 0; }
        if(arg == "--demo") {
            for(uint64_t seq=0;;++seq) {
                Frame f{};
                for(int y=0;y<120;++y) for(int x=0;x<160;++x) {
                    int cx=30 + (seq/2)%100;
                    int d=(x-cx)*(x-cx)+(y-60)*(y-60);
                    f[y*160+x]=29000 + y*2 + x + (d<225? 800:0);
                }
                emitFrame(f,seq); std::this_thread::sleep_for(std::chrono::milliseconds(116));
            }
        }
#ifdef __linux__
        int fd = open(arg.c_str(), O_RDWR);
        if(fd < 0) throw std::runtime_error("Cannot open " + arg + ": " + std::strerror(errno));
        if(flock(fd, LOCK_EX | LOCK_NB) < 0) throw std::runtime_error("Another Lepton Lab capture is already running");
        uint8_t mode=SPI_MODE_3, bits=8;
        uint32_t speed = argc>2 ? std::stoul(argv[2]) : 20000000;
        if(speed < 1000000 || speed > 20000000) throw std::runtime_error("SPI speed must be 1–20 MHz");
        if(ioctl(fd,SPI_IOC_WR_MODE,&mode)<0 || ioctl(fd,SPI_IOC_WR_BITS_PER_WORD,&bits)<0 || ioctl(fd,SPI_IOC_WR_MAX_SPEED_HZ,&speed)<0)
            throw std::runtime_error("SPI configuration failed");
        Assembler assembler; Frame frame; Packet packet;
        uint64_t seq=0; auto last=Clock::now();
        while(true) {
            ssize_t count=read(fd,packet.data(),packet.size());
            if(count<0 && errno==EINTR) continue;
            if(count!=ssize_t(packet.size())) throw std::runtime_error("Short or failed SPI packet read");
            if(assembler.push(packet,frame)) { emitFrame(frame,seq++); last=Clock::now(); }
            else if((packet[0]&15)==15) std::this_thread::sleep_for(std::chrono::microseconds(100));
            if(Clock::now()-last>std::chrono::seconds(3)) {
                std::cerr<<"No complete frame: resynchronising SPI. Check CS wiring and close the old viewer.\n";
                assembler.reset(); std::this_thread::sleep_for(std::chrono::milliseconds(200)); last=Clock::now();
            }
        }
#else
        throw std::runtime_error("Camera capture requires Linux on the Pi; use --demo on this computer");
#endif
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
