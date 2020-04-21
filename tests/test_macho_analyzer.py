import pathlib

import pytest

from strongarm.macho.macho_analyzer import MachoAnalyzer, ObjcMsgSendXref, VirtualMemoryPointer
from strongarm.macho.macho_parse import MachoParser
from strongarm.objc import ObjcFunctionAnalyzer


class TestMachoAnalyzer:
    FAT_PATH = pathlib.Path(__file__).parent / "bin" / "StrongarmTarget"

    def setup_method(self):
        parser = MachoParser(self.FAT_PATH)
        self.binary = parser.slices[0]
        self.analyzer = MachoAnalyzer.get_analyzer(self.binary)

    def test_imp_for_selref(self):
        # selref for -[DTLabel configureLabel]
        imp_within_bin_selref = VirtualMemoryPointer(0x100009078)
        found_imp_address = self.analyzer.imp_for_selref(imp_within_bin_selref)
        correct_imp_address = VirtualMemoryPointer(0x100006284)
        assert found_imp_address == correct_imp_address

        # selref for -[UIFont systemFontOfSize:]
        imp_outside_bin_selref = VirtualMemoryPointer(0x100009088)
        assert self.analyzer.imp_for_selref(imp_outside_bin_selref) is None

        imp_nonexisting = None
        assert self.analyzer.imp_for_selref(imp_nonexisting) is None

    def test_find_function_boundary(self):
        start_addr = VirtualMemoryPointer(0x100006420)
        correct_end_addr = VirtualMemoryPointer(0x100006530)

        found_instructions = self.analyzer.get_function_instructions(start_addr)
        assert len(found_instructions) == 69
        found_end_addr = found_instructions[-1].address
        assert found_end_addr == correct_end_addr

    def test_get_function_boundaries(self):
        correct_entry_points = [
            0x100006228,
            0x100006284,
            0x100006308,
            0x1000063B0,
            0x1000063E8,
            0x100006420,
            0x100006534,
            0x100006590,
            0x1000065EC,
            0x10000665C,
            0x1000066DC,
            0x1000066E4,
            0x1000066E8,
            0x1000066EC,
            0x1000066F0,
            0x1000066F4,
            0x1000066F8,
            0x100006708,
            0x10000671C,
        ]
        boundaries = self.analyzer.get_function_boundaries()
        entry_points, end_addresses = zip(*sorted(boundaries))
        assert list(entry_points) == correct_entry_points
        assert list(end_addresses) == correct_entry_points[1:] + [0x100006730]

    def test_get_function_end_address(self):
        start_addr = VirtualMemoryPointer(0x100006420)
        correct_end_addr = VirtualMemoryPointer(0x100006534)

        end_address = self.analyzer.get_function_end_address(start_addr)
        assert end_address == correct_end_addr

    def test_find_imported_symbols(self):
        correct_imported_symbols = [
            "_NSClassFromString",
            "_NSLog",
            "_NSStringFromCGRect",
            "_NSStringFromClass",
            "_OBJC_CLASS_$_NSObject",
            "_OBJC_CLASS_$_NSURLCredential",
            "_OBJC_CLASS_$_UIFont",
            "_OBJC_CLASS_$_UILabel",
            "_OBJC_CLASS_$_UIResponder",
            "_OBJC_CLASS_$_UIViewController",
            "_OBJC_METACLASS_$_NSObject",
            "_OBJC_METACLASS_$_UILabel",
            "_OBJC_METACLASS_$_UIResponder",
            "_OBJC_METACLASS_$_UIViewController",
            "_SecTrustEvaluate",
            "_UIApplicationMain",
            "___CFConstantStringClassReference",
            "__objc_empty_cache",
            "_dlopen",
            "_objc_autoreleasePoolPop",
            "_objc_autoreleasePoolPush",
            "_objc_getClass",
            "_objc_msgSend",
            "_objc_msgSendSuper2",
            "_objc_release",
            "_objc_retain",
            "_objc_retainAutoreleasedReturnValue",
            "_objc_storeStrong",
            "_rand",
            "dyld_stub_binder",
        ]
        found_imported_symbols = self.analyzer.imported_symbols
        # we don't want the test to fail if the arrays contain the same elements but in a different order
        # so, sort the arrays before comparing them
        assert sorted(found_imported_symbols) == sorted(correct_imported_symbols)

    def test_find_exported_symbols(self):
        assert self.analyzer.exported_symbol_pointers_to_names == {4294967296: "__mh_execute_header"}
        assert self.analyzer.exported_symbol_names_to_pointers == {"__mh_execute_header": 4294967296}

    def test_cached_analyzer(self):
        # there should only be one MachoAnalyzer for a given MachoBinary
        analyzer1 = MachoAnalyzer.get_analyzer(self.binary)
        analyzer2 = MachoAnalyzer.get_analyzer(self.binary)
        assert analyzer1 == analyzer2

    def test_external_symbol_addr_map(self):
        sym_map = self.analyzer.dyld_bound_symbols
        imported_syms = self.analyzer.imported_symbols
        # make sure all the symbols listed in imported_symbols are present here
        for sym in sym_map.values():
            name = sym.name
            assert name in imported_syms

        # make sure all addresses from stubs have been mapped to real destination addresses
        stubs_map = self.analyzer.imp_stubs
        call_destinations = [d.destination for d in stubs_map]
        for call_destination in call_destinations:
            assert call_destination in sym_map.keys()

    def test_find_dyld_bound_symbols(self):
        bound_symbols = self.analyzer.dyld_bound_symbols
        correct_bound_symbols = {
            0x1000090F8: "_OBJC_CLASS_$_NSURLCredential",
            0x1000091F0: "_OBJC_CLASS_$_NSObject",
            0x100009148: "_OBJC_METACLASS_$_NSObject",
            0x100009198: "_OBJC_METACLASS_$_NSObject",
            0x1000091C0: "_OBJC_METACLASS_$_NSObject",
            0x1000091C8: "_OBJC_METACLASS_$_NSObject",
            0x100009210: "_OBJC_METACLASS_$_NSObject",
            0x100009130: "__objc_empty_cache",
            0x100009158: "__objc_empty_cache",
            0x100009180: "__objc_empty_cache",
            0x1000091A8: "__objc_empty_cache",
            0x1000091D0: "__objc_empty_cache",
            0x1000091F8: "__objc_empty_cache",
            0x100009220: "__objc_empty_cache",
            0x100009248: "__objc_empty_cache",
            0x100008000: "dyld_stub_binder",
            0x100008098: "___CFConstantStringClassReference",
            0x1000080B8: "___CFConstantStringClassReference",
            0x1000080D8: "___CFConstantStringClassReference",
            0x1000080F8: "___CFConstantStringClassReference",
            0x100008118: "___CFConstantStringClassReference",
            0x100008138: "___CFConstantStringClassReference",
            0x100008158: "___CFConstantStringClassReference",
            0x1000090F0: "_OBJC_CLASS_$_UIFont",
            0x100009128: "_OBJC_CLASS_$_UILabel",
            0x100009240: "_OBJC_CLASS_$_UIResponder",
            0x100009178: "_OBJC_CLASS_$_UIViewController",
            0x100009150: "_OBJC_METACLASS_$_UILabel",
            0x100009218: "_OBJC_METACLASS_$_UIResponder",
            0x1000091A0: "_OBJC_METACLASS_$_UIViewController",
            0x100008010: "_NSClassFromString",
            0x100008018: "_NSLog",
            0x100008020: "_NSStringFromCGRect",
            0x100008028: "_NSStringFromClass",
            0x100008030: "_SecTrustEvaluate",
            0x100008038: "_UIApplicationMain",
            0x100008040: "_dlopen",
            0x100008048: "_objc_autoreleasePoolPop",
            0x100008050: "_objc_autoreleasePoolPush",
            0x100008058: "_objc_getClass",
            0x100008060: "_objc_msgSend",
            0x100008068: "_objc_msgSendSuper2",
            0x100008070: "_objc_release",
            0x100008078: "_objc_retain",
            0x100008080: "_objc_retainAutoreleasedReturnValue",
            0x100008088: "_objc_storeStrong",
            0x100008090: "_rand",
        }
        assert sorted(bound_symbols) == sorted(correct_bound_symbols)

    def test_symbol_name_for_branch_destination(self):
        # bogus destination
        with pytest.raises(RuntimeError):
            self.analyzer.symbol_name_for_branch_destination(0xDEADBEEF)

        # objc_msgSend
        assert self.analyzer.symbol_name_for_branch_destination(0x10000676C) == "_UIApplicationMain"

    def test_selref_to_name_map(self):
        correct_selref_to_imp_map = {
            0x100009070: 0x100006228,
            0x100009078: 0x100006284,
            0x1000090B8: 0x1000063E8,
            0x1000090B0: 0x1000063B0,
        }
        # did analyzer map all selrefs?
        for selref in correct_selref_to_imp_map:
            assert self.analyzer.imp_for_selref(selref) == correct_selref_to_imp_map[selref]

        # can we get an IMP from a selref?
        assert self.analyzer.imp_for_selref(0x100009070) == 0x100006228

        # nonexistent or missing selref handled correctly?
        assert self.analyzer.imp_for_selref(None) is None
        assert self.analyzer.imp_for_selref(0xDEADBEEF) is None

        # TODO(PT): handle checking selref which is defined outside binary

    def test_read_imported_symbol_pointers(self):
        # Given the binary's imported symbol pointers are the following values
        # Given the binary contains imported symbol stubs with the following values
        correct_imp_stub_address_to_sym_name = {
            4294993712: "_NSClassFromString",
            4294993724: "_NSLog",
            4294993736: "_NSStringFromCGRect",
            4294993748: "_NSStringFromClass",
            4294993760: "_SecTrustEvaluate",
            4294993772: "_UIApplicationMain",
            4294993784: "_dlopen",
            4294993796: "_objc_autoreleasePoolPop",
            4294993808: "_objc_autoreleasePoolPush",
            4294993820: "_objc_getClass",
            4294993832: "_objc_msgSend",
            4294993844: "_objc_msgSendSuper2",
            4294993856: "_objc_release",
            4294993868: "_objc_retain",
            4294993880: "_objc_retainAutoreleasedReturnValue",
            4294993892: "_objc_storeStrong",
            4294993904: "_rand",
        }
        # If I ask strongarm to retrieve the map of stubs to imported symbol names
        found_imp_stub_to_sym_name = self.analyzer.imp_stubs_to_symbol_names
        # Then I find the correct data
        assert found_imp_stub_to_sym_name == correct_imp_stub_address_to_sym_name

    def test_read_xref(self):
        # When I ask for an XRef
        # Then I get the correct data
        xrefs = self.analyzer.calls_to(VirtualMemoryPointer(0x100006748))
        assert len(xrefs) == 1
        xref = xrefs[0]
        assert xref.caller_func_start_address == VirtualMemoryPointer(0x100006308)
        assert xref.caller_addr == 0x100006350

        method_info = self.analyzer.method_info_for_entry_point(xref.caller_func_start_address)
        assert method_info

        # TODO(PT): ObjcFunctionAnalyzer.get_function_analyzer* should return singletons
        caller_func = ObjcFunctionAnalyzer.get_function_analyzer_for_method(self.analyzer.binary, method_info)
        assert caller_func.method_info.objc_class.name == "DTLabel"
        assert caller_func.method_info.objc_sel.name == "logLabel"

    def test_find_symbols_by_address(self):
        # Given I provide a locally-defined callable symbol (__mh_execute_header)
        # If I ask for the information about this symbol
        addr = VirtualMemoryPointer(0x100000000)
        symbol = self.analyzer.callable_symbol_for_address(addr)
        # Then it is reported correctly
        assert symbol.is_imported is False
        assert symbol.address == addr
        assert symbol.symbol_name == "__mh_execute_header"

        # Given I provide an externally-defined imported symbol (_objc_msgSend)
        # If I ask for the information about this symbol
        addr = VirtualMemoryPointer(0x1000067A8)
        symbol = self.analyzer.callable_symbol_for_address(addr)
        # Then it is reported correctly
        assert symbol.is_imported is True
        assert symbol.address == addr
        assert symbol.symbol_name == "_objc_msgSend"

        # Given I provide a branch destination which does not have an associated symbol name (an anonymous label)
        addr = VirtualMemoryPointer(0x100006270)
        symbol = self.analyzer.callable_symbol_for_address(addr)
        # Then no named symbol is returned
        assert symbol is None

    def test_find_symbols_by_name(self):
        # Given I provide a locally-defined callable symbol (__mh_execute_header)
        # If I ask for the information about this symbol
        symbol = self.analyzer.callable_symbol_for_symbol_name("__mh_execute_header")
        # Then it is reported correctly
        assert symbol.is_imported is False
        assert symbol.address == VirtualMemoryPointer(0x100000000)
        assert symbol.symbol_name == "__mh_execute_header"

        # Given I provide an externally-defined imported symbol (_objc_msgSend)
        # If I ask for the information about this symbol
        symbol = self.analyzer.callable_symbol_for_symbol_name("_objc_msgSend")
        # Then it is reported correctly
        assert symbol.is_imported is True
        assert symbol.address == VirtualMemoryPointer(0x1000067A8)
        assert symbol.symbol_name == "_objc_msgSend"

        # Given I provide a symbol name that is not present in the binary
        symbol = self.analyzer.callable_symbol_for_symbol_name("_fake_symbol")
        # Then no named symbol is returned
        assert symbol is None


class TestMachoAnalyzerDynStaticChecks:
    FAT_PATH = pathlib.Path(__file__).parent / "bin" / "DynStaticChecks"

    def setup_method(self):
        parser = MachoParser(self.FAT_PATH)
        self.binary = parser.slices[0]
        self.analyzer = MachoAnalyzer.get_analyzer(self.binary)

    def test_get_function_boundaries(self):
        correct_entry_points = [
            0x100007B1C,
            0x100007BD8,
            0x100007C94,
            0x100007D50,
            0x100007E0C,
            0x100007EC8,
            0x100007F84,
            0x100007FE4,
            0x1000080D0,
            0x100008158,
            0x1000081CC,
            0x100008254,
            0x1000082C8,
            0x100008350,
            0x1000083C4,
            0x1000083FC,
            0x100008434,
            0x10000849C,
            0x100008504,
            0x1000085F0,
            0x100008610,
            0x100008690,
            0x100008774,
            0x1000087F0,
            0x100008864,
            0x1000089EC,
            0x100008AB8,
            0x100008B48,
            0x100008C3C,
            0x100008D6C,
            0x100008E4C,
            0x100008F3C,
            0x100008F50,
            0x10000901C,
            0x1000090A4,
            0x100009104,
            0x100009188,
            0x10000920C,
            0x100009274,
            0x1000092E4,
            0x1000093A4,
            0x1000093D8,
            0x100009460,
            0x10000950C,
            0x100009584,
            0x100009604,
            0x100009688,
            0x100009700,
            0x1000097EC,
            0x1000097F4,
            0x1000097F8,
            0x1000097FC,
            0x100009800,
            0x100009804,
            0x100009808,
            0x100009818,
            0x10000982C,
            0x100009840,
            0x10000992C,
            0x100009968,
            0x1000099A8,
            0x1000099E8,
            0x100009A64,
            0x100009AE4,
            0x100009B64,
            0x100009BB4,
            0x100009C08,
            0x100009C5C,
            0x100009CE8,
            0x100009D78,
            0x100009E08,
            0x100009E50,
        ]
        correct_entry_points = list(map(VirtualMemoryPointer, correct_entry_points))
        boundaries = self.analyzer.get_function_boundaries()
        entry_points, end_addresses = zip(*sorted(boundaries))
        assert list(entry_points) == correct_entry_points
        assert list(end_addresses) == correct_entry_points[1:] + [0x100009EA8]

    def test_get_function_end_address(self):
        test_cases = (
            # -[PTObjectTracking earlyReturn] defined at 0x100008e4c
            (0x100008E4C, 0x100008F3C),
            # -[PTObjectTracking .cxx_destruct] defined at 0x100008f3c
            (0x100008F3C, 0x100008F50),
            # -[ITJRSA SecKeyDecryptStaticPrivateKey] defined at 0x10000901c
            (0x10000901C, 0x1000090A4),
            # -[ITJCCKeyDerivationPBKDF lowRoundCount] defined at 0x100009604
            (0x100009604, 0x100009688),
        )
        for entry_point, expected_end_address in test_cases:
            end_address = self.analyzer.get_function_end_address(entry_point)
            assert end_address == expected_end_address

    def test_xref_objc_opt_new(self):
        # Given I provide a binary which contains the code:
        # _objc_opt_new(_OBJC_CLASS_$_ARSKView)
        binary = MachoParser(pathlib.Path(__file__).parent / "bin" / "iOS13_objc_opt").get_arm64_slice()
        analyzer = MachoAnalyzer.get_analyzer(binary)

        # When I ask for XRefs to `ARSKView`
        arskview_classref = analyzer.classref_for_class_name("_OBJC_CLASS_$_ARSKView")
        assert arskview_classref
        objc_calls = analyzer.objc_calls_to(
            objc_classrefs=[arskview_classref], objc_selrefs=[], requires_class_and_sel_found=False
        )

        # Then the code location is returned
        assert len(objc_calls) == 1

        call = objc_calls[0]
        assert call == ObjcMsgSendXref(
            caller_func_start_address=VirtualMemoryPointer(0x100006388),
            caller_addr=VirtualMemoryPointer(0x1000063B4),
            destination_addr=VirtualMemoryPointer(0x10000659C),
            classref=VirtualMemoryPointer(0x10000D398),
            selref=VirtualMemoryPointer(0x0),
        )

        # TODO(PT): Update this unit test once this functionality is added
        # And when I ask for XRefs to `[ARSKView new]`
        # Then the code location is returned

        # And when I ask for XRefs to `new`
        # Then the code location is returned

    def test_xref_objc_opt_class(self):
        # Given I provide a binary which contains the code:
        # _objc_opt_class(_OBJC_CLASS_$_ARFaceTrackingConfiguration)
        binary = MachoParser(pathlib.Path(__file__).parent / "bin" / "iOS13_objc_opt").get_arm64_slice()
        analyzer = MachoAnalyzer.get_analyzer(binary)

        # When I ask for XRefs to `ARSKView`
        arfacetracking_classref = analyzer.classref_for_class_name("_OBJC_CLASS_$_ARFaceTrackingConfiguration")
        assert arfacetracking_classref
        objc_calls = analyzer.objc_calls_to(
            objc_classrefs=[arfacetracking_classref], objc_selrefs=[], requires_class_and_sel_found=False
        )

        # Then the code location is returned
        assert len(objc_calls) == 1
        assert objc_calls[0] == ObjcMsgSendXref(
            caller_func_start_address=VirtualMemoryPointer(0x100006388),
            caller_addr=VirtualMemoryPointer(0x10000639C),
            destination_addr=VirtualMemoryPointer(0x100006590),
            classref=VirtualMemoryPointer(0x10000D390),
            selref=VirtualMemoryPointer(0x0),
        )

        # TODO(PT): Update this unit test once this functionality is added
        # And when I ask for XRefs to `[ARFaceTrackingConfiguration class]`
        # Then the code location is returned

        # And when I ask for XRefs to `class`
        # Then the code location is returned


class TestMachoAnalyzerControlFlowTarget:
    FAT_PATH = pathlib.Path(__file__).parent / "bin" / "StrongarmControlFlowTarget"

    def setup_method(self):
        parser = MachoParser(self.FAT_PATH)
        self.binary = parser.slices[0]
        self.analyzer = MachoAnalyzer.get_analyzer(self.binary)

    def test_get_function_end_address(self):
        test_cases = (
            # -[CFDataFlowMethods switchControlFlow] defined at 0x10000675c
            (0x10000675C, 0x1000067F4),
        )
        for entry_point, expected_end_address in test_cases:
            end_address = self.analyzer.get_function_end_address(entry_point)
            assert end_address == expected_end_address
