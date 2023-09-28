//go:build testing && jemalloc

package zippdb

import (
	"testing"

	"github.com/stretchr/testify/require"
)

func TestMemAlloc(t *testing.T) {
	m, err := CreateJemallocNodumpAllocator()
	require.NoError(t, err)
	m.Destroy()
}
