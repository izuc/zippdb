package zippdb

// #include "zippdb/c.h"
import "C"

// EnvOptions represents options for env.
type EnvOptions struct {
	c *C.rocksdb_envoptions_t
}

// NewDefaultEnvOptions creates a default EnvOptions object.
func NewDefaultEnvOptions() *EnvOptions {
	return newNativeEnvOptions(C.rocksdb_envoptions_create())
}

// NewNativeEnvOptions creates a EnvOptions object.
func newNativeEnvOptions(c *C.rocksdb_envoptions_t) *EnvOptions {
	return &EnvOptions{c: c}
}

// Destroy deallocates the EnvOptions object.
func (opts *EnvOptions) Destroy() {
	C.rocksdb_envoptions_destroy(opts.c)
	opts.c = nil
}
