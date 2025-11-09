#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <linux/memfd.h>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <fstream>

extern "C" {

struct IsolationResult {
    int success;
    int fd;
    unsigned long long size;
    char message[256];
};

static void set_error(IsolationResult &result, const std::string &msg) {
    result.success = 0;
    result.fd = -1;
    result.size = 0;
    std::strncpy(result.message, msg.c_str(), sizeof(result.message) - 1);
    result.message[sizeof(result.message) - 1] = '\0';
}

IsolationResult isolate_file(const char *source_path, const char *session_name) {
    IsolationResult result{};
    result.success = 0;
    result.fd = -1;
    result.size = 0;
    result.message[0] = '\0';

    if (!source_path || !session_name) {
        set_error(result, "Invalid arguments");
        return result;
    }

    int fd = memfd_create(session_name, MFD_CLOEXEC | MFD_ALLOW_SEALING);
    if (fd == -1) {
        set_error(result, std::string("memfd_create failed: ") + std::strerror(errno));
        return result;
    }

    std::ifstream input(source_path, std::ios::in | std::ios::binary);
    if (!input.good()) {
        close(fd);
        set_error(result, "Unable to open source file");
        return result;
    }

    constexpr std::size_t BUFFER_SIZE = 1 << 16;
    char buffer[BUFFER_SIZE];
    unsigned long long total = 0ULL;
    while (input.good()) {
        input.read(buffer, BUFFER_SIZE);
        std::streamsize count = input.gcount();
        if (count <= 0) {
            break;
        }
        const char *write_ptr = buffer;
        std::streamsize remaining = count;
        while (remaining > 0) {
            ssize_t written = ::write(fd, write_ptr, static_cast<size_t>(remaining));
            if (written == -1) {
                int err = errno;
                close(fd);
                set_error(result, std::string("write failed: ") + std::strerror(err));
                return result;
            }
            remaining -= written;
            write_ptr += written;
        }
        total += static_cast<unsigned long long>(count);
    }

    if (input.bad()) {
        int err = errno;
        close(fd);
        set_error(result, std::string("read failed: ") + std::strerror(err));
        return result;
    }

    // Seal the memfd to prevent further modification
    int seals = F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE;
    if (fcntl(fd, F_ADD_SEALS, seals) == -1) {
        int err = errno;
        close(fd);
        set_error(result, std::string("fcntl seal failed: ") + std::strerror(err));
        return result;
    }

    result.success = 1;
    result.fd = fd;
    result.size = total;
    result.message[0] = '\0';
    return result;
}

int export_fd(int fd, const char *destination_path) {
    if (fd < 0 || !destination_path) {
        errno = EINVAL;
        return -1;
    }

    std::ifstream source(std::string("/proc/self/fd/") + std::to_string(fd), std::ios::in | std::ios::binary);
    if (!source.good()) {
        errno = EBADF;
        return -1;
    }

    std::ofstream dest(destination_path, std::ios::out | std::ios::binary | std::ios::trunc);
    if (!dest.good()) {
        return -1;
    }

    constexpr std::size_t BUFFER_SIZE = 1 << 16;
    char buffer[BUFFER_SIZE];
    while (source.good()) {
        source.read(buffer, BUFFER_SIZE);
        std::streamsize count = source.gcount();
        if (count <= 0) {
            break;
        }
        dest.write(buffer, count);
        if (!dest.good()) {
            return -1;
        }
    }

    dest.flush();
    if (!dest.good()) {
        return -1;
    }

    if (::chmod(destination_path, S_IRUSR | S_IRGRP | S_IROTH) == -1) {
        return -1;
    }

    return 0;
}

int close_fd(int fd) {
    if (fd < 0) {
        errno = EINVAL;
        return -1;
    }
    return ::close(fd);
}

}
