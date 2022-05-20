import gdb as g

'''
@global Task        task    'struct task_struct' of poc process
@global Pipe        pipe    'struct pipe_inode_info' of our pipe
@global PipeBuffer  buf     'struct pipe_buffer' of our pipe
@global AddrSpace   fmap    'struct address_space' representing the
                            target target file in the page cache
'''
task = None
pipe = None
buf = None
fmap = None

class GenericStruct():
    def __init__(self, address):
        '''
        @param gdb.Value address: pointer to struct
        '''
        self.address = address

    def get_member(self, member):
        '''
        @param String member: struct member to get
        '''
        return self.address.dereference()[member]

    def print_member(self, member):
        '''
        @param String member: struct member to print
        '''
        print("> '{0}': {1}".format(member, self.get_member(member)))

    def print_header(self):
        '''
        Info: prints type and address of the struct.
        '''
        # TODO use classvarible type
        print("{0} at {1}".format(self.address.dereference().type,
                                    self.address))

    def print_info(self):
        '''
        Info: Prints summary including 'interesting' members of the 
          struct. 
        '''
        self.print_header()
        self._print_info()
        print('')

    def _print_info(self):
        '''
        Implement yourself when subclassing.
        '''
        pass

class Task(GenericStruct):
    def _print_info(self):
        self.print_member('pid')
        self.print_member('comm')

class Pipe(GenericStruct):
    def _print_info(self):
        self.print_member('head')
        self.print_member('tail')
        self.print_member('ring_size')
        self.print_member('bufs')

class PipeBuffer(GenericStruct):
    def _print_info(self):
        print(self.address.dereference())

class AddrSpace(GenericStruct):
    def _print_info(self):
        print("> 'i_pages.xa_head' : {0}".format(
            self.get_member('i_pages')['xa_head']))

class XArray(GenericStruct):
    def _print_info(self):
        pass

class Page(GenericStruct):
    # TODO this belongs into parent class
    stype = g.lookup_type('struct page')
    ptype = stype.pointer()

    def __init__(self, address):
        '''
        @attr   gdb.Value   virtual     virtual address of cached data
        '''
        # TODO this belongs into parent class
        if address.type != Page.ptype:
            address = address.cast(Page.ptype)
        super().__init__(address)
        self.virtual = self.page_address(self.address)

    @staticmethod
    def page_address(page):
        '''
        Info: Calculates the virtual address of a page
        @param  gdb.Value   page        'struct page *'
        '''
        vmemmap_base = int(g.parse_and_eval('vmemmap_base'))
        page_offset_base = int(g.parse_and_eval('page_offset_base'))
        page = int(page)
        return (int((page - vmemmap_base)/64) << 12) + page_offset_base

    def _print_info(self):
        print("> data: "+g.selected_inferior().read_memory(self.virtual, 19).tobytes().decode('ASCII'))



class PipeBP(g.Breakpoint):
    def stop(self):
        global pipe, task
        task = Task(g.parse_and_eval('$lx_current()').address)
        pipe = Pipe(g.parse_and_eval('pipe'))
        buf = PipeBuffer(pipe.get_member('bufs'))
        print(75*"-"+"\nStage 1: create fresh pipe\n")
        task.print_info()
        pipe.print_info()
        buf.print_info()
        return False

class BufReleaseBP(g.Breakpoint):
    def stop(self):
        global pipe, buf, task
        buf = PipeBuffer(pipe.get_member('bufs'))
        print(75*"-"+"\nStage 4: release drained pipe buffer\n")
        task.print_info()
        pipe.print_info()
        buf.print_info()
        return False

class CopyPageBP(g.Breakpoint):
    def stop(self):
        global writebp, fmap, pipe, buf, task
        writebp.enabled = True # TOOD implement proper
        fmap = AddrSpace(g.parse_and_eval(
            '$lx_current().files.fdt.fd[3].f_inode.i_mapping'))
        xarray = XArray(fmap.get_member('i_pages').address)
        page = Page(xarray.get_member('xa_head'))
        print(75*"-"+"\nStage 5: splicing file to pipe\n")
        task.print_info()
        pipe.print_info()
        buf.print_info()
        fmap.print_info()
        page.print_info()
        return True

class WriteBP(g.Breakpoint):
    def stop(self):
        global task, pipe, buf, fmap
        print(75*"-"+"\nStage 6: writing to page cache\n")
        task.print_info()
        pipe.print_info()
        buf.print_info()
        fmap.print_info()
        g.execute('q')
        return False

PipeBP('fs/pipe.c:885')
BufReleaseBP('anon_pipe_buf_release')
CopyPageBP('*0xffffffff8142005b', g.BP_HARDWARE_BREAKPOINT)
writebp = WriteBP('*0xffffffff8120c94e', g.BP_HARDWARE_BREAKPOINT)
writebp.enabled = False
g.execute('c')
