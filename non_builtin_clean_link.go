//go:build !testing && zippdb_clean_link

package zippdb

// #cgo LDFLAGS: -lrocksdb -pthread -lstdc++ -ldl
import "C"
