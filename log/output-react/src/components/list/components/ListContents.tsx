import { FC, HTMLProps, useCallback, useEffect, useMemo, useRef } from 'react';
import { VariableSizeList } from 'react-window';
import { Box, useSize } from '@robocorp/components';
import { styled } from '@robocorp/theme';

import { RowCellsContainer } from '../../row/RowCellsContainer';
import { getLogEntryHeight, useLogContext } from '~/lib';

type Props = HTMLProps<HTMLDivElement>;

const Container = styled(Box)`
  height: calc(100% - ${({ theme }) => theme.sizes.$56});
  min-height: 0;
  overflow: hidden;
`;

export const ListContents: FC<Props> = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<VariableSizeList>(null);
  const { height } = useSize(containerRef);
  const { filteredEntries, lastUpdatedIndex } = useLogContext();

  useEffect(() => {
    listRef.current?.resetAfterIndex(lastUpdatedIndex.current);
  });

  const itemCount = useMemo(() => {
    return filteredEntries.entries.length;
  }, [filteredEntries]);

  const itemSize = useCallback(
    (itemIndex: number) => {
      const size = getLogEntryHeight(filteredEntries.entries[itemIndex]);
      return size;
    },
    [filteredEntries],
  );

  return (
    <Container ref={containerRef}>
      <VariableSizeList
        ref={listRef}
        height={height}
        width="100%"
        itemCount={itemCount}
        itemSize={itemSize}
        estimatedItemSize={32}
      >
        {RowCellsContainer}
      </VariableSizeList>
    </Container>
  );
};
